"""
TravelOps 360 — Event Producer
Replays flight-status, baggage-scan and booking events from the Silver layer
onto Kafka in (roughly) event-time order, at accelerated speed, to simulate a
live airport-operations feed.

To give the consumer real work to prove its retry / dedup / out-of-order
handling, this producer deliberately:
  - re-sends ~1% of events (duplicate delivery, the way a retried producer
    or an at-least-once broker would)
  - sends ~2% of events slightly out of event-time order
  - drops the connection and reconnects a few times per run (retry proof)

Run:
  python3 streaming/producer.py --speed 500 --limit 20000
"""
import argparse
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone

import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

ROOT = os.path.join(os.path.dirname(__file__), "..")
SILVER = os.path.join(ROOT, "data", "silver")

TOPICS = {
    "flight_status": "flights.status",
    "baggage_scan": "baggage.scans",
    "booking": "bookings.events",
}


def make_producer(bootstrap="localhost:9092"):
    for attempt in range(1, 6):
        try:
            return KafkaProducer(
                bootstrap_servers=bootstrap,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8"),
                acks="all",              # wait for full ISR ack — no silent data loss
                retries=5,                # built-in producer-side retry on transient errors
                linger_ms=20,
                enable_idempotence=True,  # broker-side dedup of producer retries (exactly-once per session)
            )
        except KafkaError as e:
            wait = 2 ** attempt
            print(f"[producer] connect failed ({e}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Could not connect to Kafka after 5 attempts")


def load_events(limit: int) -> list[dict]:
    flights = pd.read_parquet(f"{SILVER}/flights.parquet")
    baggage = pd.read_parquet(f"{SILVER}/baggage.parquet")
    bookings = pd.read_parquet(f"{SILVER}/bookings.parquet")

    events = []
    for _, r in flights.head(limit // 3).iterrows():
        events.append({
            "event_id": str(uuid.uuid4()),
            "event_type": "flight_status",
            "topic": TOPICS["flight_status"],
            "key": r["flight_id"],
            "event_time": str(r["scheduled_departure"]),
            "payload": {
                "flight_id": r["flight_id"], "route_id": r["route_id"],
                "aircraft_id": r["aircraft_id"], "status": r["status"],
                "scheduled_departure": str(r["scheduled_departure"]),
                "actual_departure": str(r["actual_departure"]) if pd.notna(r["actual_departure"]) else None,
                "delay_minutes": None if pd.isna(r["delay_minutes"]) else float(r["delay_minutes"]),
            },
        })
    for _, r in baggage.head(limit // 3).iterrows():
        events.append({
            "event_id": str(uuid.uuid4()),
            "event_type": "baggage_scan",
            "topic": TOPICS["baggage_scan"],
            "key": r["bag_id"],
            "event_time": str(r["scan_time"]),
            "payload": {
                "bag_id": r["bag_id"], "booking_id": r["booking_id"],
                "airport": r["airport"], "status": r["status"],
                "scan_time": str(r["scan_time"]),
            },
        })
    for _, r in bookings.head(limit // 3).iterrows():
        events.append({
            "event_id": str(uuid.uuid4()),
            "event_type": "booking",
            "topic": TOPICS["booking"],
            "key": r["booking_id"],
            "event_time": str(r["booking_time"]),
            "payload": {
                "booking_id": r["booking_id"], "customer_id": r["customer_id"],
                "flight_id": r["flight_id"], "fare": float(r["fare"]),
                "status": r["status"], "booking_time": str(r["booking_time"]),
            },
        })

    events.sort(key=lambda e: e["event_time"])
    return events


def inject_chaos(events: list[dict], dup_rate=0.01, ooo_rate=0.02) -> list[dict]:
    """Duplicate ~dup_rate of events and shuffle ~ooo_rate slightly out of order,
    so the consumer's dedup/out-of-order handling has real cases to prove."""
    out = list(events)
    n_dup = int(len(events) * dup_rate)
    for e in random.sample(events, min(n_dup, len(events))):
        out.append(dict(e))  # same event_id -> true duplicate delivery
    for i in range(len(out) - 1):
        if random.random() < ooo_rate:
            out[i], out[i + 1] = out[i + 1], out[i]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default=os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092"))
    ap.add_argument("--speed", type=int, default=500, help="events/sec (approx)")
    ap.add_argument("--limit", type=int, default=15000, help="max events to replay")
    args = ap.parse_args()

    events = inject_chaos(load_events(args.limit))
    producer = make_producer(args.bootstrap)
    delay = 1.0 / max(args.speed, 1)

    sent, failed = 0, 0
    for i, e in enumerate(events):
        e["_produced_at"] = datetime.now(timezone.utc).isoformat()
        try:
            producer.send(e["topic"], key=e["key"], value=e).get(timeout=10)  # sync send = proves delivery
            sent += 1
        except KafkaError as ex:
            failed += 1
            print(f"[producer] send failed for {e['event_id']}: {ex}")
        if i % 500 == 0 and i > 0:
            print(f"[producer] {i}/{len(events)} sent (incl. injected duplicates/reorders)")
            if i % 5000 == 0:
                print("[producer] simulating a transient disconnect + reconnect...")
                producer.flush()
                producer.close()
                time.sleep(1.5)
                producer = make_producer(args.bootstrap)
        time.sleep(delay)

    producer.flush()
    producer.close()
    print(f"[producer] done. sent={sent} failed={failed} total_events(incl. chaos)={len(events)}")


if __name__ == "__main__":
    main()
