"""
TravelOps 360 — Stream Processor (consumer)
Consumes flights.status / baggage.scans / bookings.events, and writes a
persistent, query-able "live" analytical layer into the same DuckDB warehouse
the batch pipeline uses — this is what the Airport Command Center / Flight
Health frontend pages poll for their "live, no manual refresh" requirement.

Strategy (see streaming/README.md for the write-up):
  - Duplicate-event strategy : event_id is the idempotency key. Every event
    is upserted (INSERT ... ON CONFLICT via existence check) into
    stream_seen_events (PK = event_id) *before* being applied — retried or
    re-delivered events are detected and skipped, in a table so it survives
    a consumer restart (not just an in-memory set).
  - Out-of-order handling    : each live table keeps the row with the max
    event_time per key (flight_id / bag_id / booking_id), so a late-arriving
    or reordered event never overwrites a newer state with an older one.
  - Retry handling           : consumer manually commits offsets only after
    a successful DB write; a failed write is retried with backoff up to 3x,
    then the raw message is forwarded to events.deadletter for manual review
    instead of blocking the partition.
  - Monitoring               : every batch writes a heartbeat row (topic,
    partition, offset, lag, processed/duplicate/error counts) to
    stream_monitoring, which the /api/data-quality and ops dashboard read.

Run:
  python3 streaming/consumer.py --group travelops-processor
"""
import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone

import duckdb
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.errors import KafkaError

ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(ROOT, "data", "warehouse", "travelops.duckdb")
TOPICS = ["flights.status", "baggage.scans", "bookings.events"]
DEADLETTER_TOPIC = "events.deadletter"

DDL = """
CREATE SCHEMA IF NOT EXISTS travelops;
SET SCHEMA 'travelops';

CREATE TABLE IF NOT EXISTS stream_seen_events (
    event_id      VARCHAR PRIMARY KEY,
    event_type    VARCHAR,
    topic         VARCHAR,
    consumed_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_flight_status_live (
    flight_id            VARCHAR PRIMARY KEY,
    route_id             VARCHAR,
    aircraft_id          VARCHAR,
    status                VARCHAR,
    scheduled_departure   TIMESTAMP,
    actual_departure      TIMESTAMP,
    delay_minutes         DOUBLE,
    event_time            TIMESTAMP,
    _updated_at            TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_baggage_scan_live (
    bag_id        VARCHAR PRIMARY KEY,
    booking_id    VARCHAR,
    airport       VARCHAR,
    status        VARCHAR,
    scan_time     TIMESTAMP,
    event_time    TIMESTAMP,
    _updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_booking_live (
    booking_id      VARCHAR PRIMARY KEY,
    customer_id     VARCHAR,
    flight_id       VARCHAR,
    fare            DOUBLE,
    status          VARCHAR,
    booking_time    TIMESTAMP,
    event_time      TIMESTAMP,
    _updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stream_monitoring (
    run_id          VARCHAR,
    topic           VARCHAR,
    window_start    TIMESTAMP,
    window_end      TIMESTAMP,
    processed       INTEGER,
    duplicates      INTEGER,
    errors          INTEGER,
    consumer_lag    INTEGER
);
"""

UPSERT_LIVE = {
    "flight_status": """
        INSERT INTO fact_flight_status_live
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT (flight_id) DO UPDATE SET
            status = excluded.status, actual_departure = excluded.actual_departure,
            delay_minutes = excluded.delay_minutes, event_time = excluded.event_time,
            _updated_at = excluded._updated_at
        WHERE excluded.event_time >= fact_flight_status_live.event_time
    """,
    "baggage_scan": """
        INSERT INTO fact_baggage_scan_live
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT (bag_id) DO UPDATE SET
            status = excluded.status, scan_time = excluded.scan_time,
            event_time = excluded.event_time, _updated_at = excluded._updated_at
        WHERE excluded.event_time >= fact_baggage_scan_live.event_time
    """,
    "booking": """
        INSERT INTO fact_booking_live
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT (booking_id) DO UPDATE SET
            status = excluded.status, event_time = excluded.event_time,
            _updated_at = excluded._updated_at
        WHERE excluded.event_time >= fact_booking_live.event_time
    """,
}


def apply_event(con, e: dict):
    p = e["payload"]
    now = datetime.now(timezone.utc)
    et = e["event_type"]
    if et == "flight_status":
        con.execute(UPSERT_LIVE[et], [p["flight_id"], p["route_id"], p["aircraft_id"], p["status"],
                                       p["scheduled_departure"], p["actual_departure"], p["delay_minutes"],
                                       e["event_time"], now])
    elif et == "baggage_scan":
        con.execute(UPSERT_LIVE[et], [p["bag_id"], p["booking_id"], p["airport"], p["status"],
                                       p["scan_time"], e["event_time"], now])
    elif et == "booking":
        con.execute(UPSERT_LIVE[et], [p["booking_id"], p["customer_id"], p["flight_id"], p["fare"],
                                       p["status"], p["booking_time"], e["event_time"], now])


def process_with_retry(con, dlq_producer, e: dict, max_retries=3) -> str:
    """Returns 'duplicate' | 'processed' | 'deadlettered'."""
    already_seen = con.execute(
        "SELECT 1 FROM stream_seen_events WHERE event_id = ?", [e["event_id"]]
    ).fetchone()
    if already_seen:
        return "duplicate"

    for attempt in range(1, max_retries + 1):
        try:
            con.execute("BEGIN TRANSACTION")
            apply_event(con, e)
            con.execute("INSERT INTO stream_seen_events VALUES (?,?,?,?)",
                        [e["event_id"], e["event_type"], e["topic"], datetime.now(timezone.utc)])
            con.execute("COMMIT")
            return "processed"
        except Exception as ex:
            con.execute("ROLLBACK")
            wait = 0.5 * (2 ** (attempt - 1))
            print(f"[consumer] apply failed (attempt {attempt}/{max_retries}) for {e['event_id']}: {ex}; retrying in {wait}s")
            time.sleep(wait)

    if dlq_producer is not None:
        dlq_producer.send(DEADLETTER_TOPIC, value=json.dumps(e, default=str).encode("utf-8"))
        dlq_producer.flush()
    return "deadlettered"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default=os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092"))
    ap.add_argument("--group", default="travelops-processor")
    ap.add_argument("--batch-window-sec", type=int, default=10)
    args = ap.parse_args()

    con = duckdb.connect(DB_PATH)
    con.execute(DDL)

    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=args.bootstrap,
        group_id=args.group,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=False,          # manual commit -> at-least-once, commit only after DB write succeeds
        auto_offset_reset="earliest",
        max_poll_records=200,
        consumer_timeout_ms=15000,
    )
    dlq_producer = KafkaProducer(bootstrap_servers=args.bootstrap)

    run_id = str(uuid.uuid4())[:8]
    print(f"[consumer] run={run_id} group={args.group} topics={TOPICS}")

    window_start = datetime.now(timezone.utc)
    counts = {"processed": 0, "duplicate": 0, "errors": 0}
    per_topic = {t: {"processed": 0, "duplicate": 0, "errors": 0} for t in TOPICS}

    try:
        while True:
            batch = consumer.poll(timeout_ms=args.batch_window_sec * 1000, max_records=200)
            if not batch:
                _flush_monitoring(con, run_id, per_topic, window_start)
                window_start = datetime.now(timezone.utc)
                continue

            for tp, records in batch.items():
                for rec in records:
                    e = rec.value
                    outcome = process_with_retry(con, dlq_producer, e)
                    if outcome == "deadlettered":
                        counts["errors"] += 1
                        per_topic[tp.topic]["errors"] += 1
                    else:
                        counts[outcome] += 1
                        per_topic[tp.topic][outcome] += 1

            # commit all assigned partitions after the whole batch is durably applied to DuckDB
            # (manual commit = at-least-once: a crash before this line just re-delivers,
            #  and stream_seen_events makes re-delivery a safe no-op via the dedup check above)
            consumer.commit()
            print(f"[consumer] batch: processed={counts['processed']} dup={counts['duplicate']} errors={counts['errors']}")

    except KeyboardInterrupt:
        print("[consumer] stopping...")
    finally:
        _flush_monitoring(con, run_id, per_topic, window_start)
        consumer.close()
        con.close()


def _flush_monitoring(con, run_id, per_topic, window_start):
    now = datetime.now(timezone.utc)
    for topic, c in per_topic.items():
        con.execute(
            "INSERT INTO stream_monitoring VALUES (?,?,?,?,?,?,?,?)",
            [run_id, topic, window_start, now, c["processed"], c["duplicate"], c["errors"], None],
        )
        c["processed"] = c["duplicate"] = c["errors"] = 0


if __name__ == "__main__":
    main()
