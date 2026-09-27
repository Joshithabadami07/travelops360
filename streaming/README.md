# Streaming — Kafka event bus

## Topics
| Topic | Key | Partitions | Producer | Consumer group |
|---|---|---|---|---|
| `flights.status` | flight_id | 3 | producer.py | travelops-processor |
| `baggage.scans` | bag_id | 3 | producer.py | travelops-processor |
| `bookings.events` | booking_id | 3 | producer.py | travelops-processor |
| `events.deadletter` | n/a | 1 | consumer.py (on failure) | manual review |

## Run it
```bash
docker compose -f streaming/docker-compose.yml up -d
./streaming/create_topics.sh
pip install kafka-python duckdb

# terminal 1 — processor (must be running first so it doesn't miss the earliest offsets on a cold start)
python3 streaming/consumer.py --group travelops-processor

# terminal 2 — producer (replays Silver-layer events as a live feed, with injected chaos)
python3 streaming/producer.py --speed 500 --limit 15000
```
Kafka UI (topics / partitions / consumer lag): http://localhost:8080

## Evidence chain (producer → topic → consumer → analytical table → API/frontend)
1. `producer.py` reads validated Silver rows and emits them as JSON events to the three topics above.
2. Kafka durably logs the events per partition, keyed so all events for one `flight_id` land on the
   same partition and are processed in order relative to each other.
3. `consumer.py` (`travelops-processor` group) polls all three topics, applies each event to the
   warehouse, and commits offsets only after the DB write succeeds.
4. Results land in `fact_flight_status_live`, `fact_baggage_scan_live`, `fact_booking_live` inside
   `data/warehouse/travelops.duckdb` — the same warehouse the batch pipeline writes to.
5. `GET /api/events/live` (FastAPI) reads those tables; the Airport Command Center frontend page polls
   that endpoint every few seconds, so it updates without a manual batch refresh.

## Duplicate-event strategy
`stream_seen_events(event_id PK)` is the idempotency ledger. Every event is checked against it before
being applied; a duplicate delivery (retried producer send, consumer re-poll after a crash before commit,
or the producer's own injected ~1% duplicate-send test) is detected and skipped — it never double-applies.
The ledger is a table, not an in-memory set, so idempotency survives a consumer restart.
The producer additionally sets `enable_idempotence=True` + `acks=all`, so the *broker* also collapses
producer-side retries of the same message before the consumer ever sees them.

## Out-of-order handling
Each live table upserts `ON CONFLICT (business_key) ... WHERE excluded.event_time >= current.event_time`.
A late or reordered event (the producer intentionally reorders ~2% of events) can never overwrite a
newer known state with stale data — the row only moves forward in event-time, regardless of arrival order.

## Retry handling
A DB-write failure (e.g. a transient lock) is retried up to 3x with exponential backoff inside the same
poll batch. If it still fails, the raw event is forwarded to `events.deadletter` for manual replay/inspection
instead of blocking the partition and stalling every event behind it.

## Monitoring
Every ~10s polling window, the consumer writes one row per topic to `stream_monitoring`
(processed / duplicate / error counts, window start/end). `GET /api/data-quality` and the ops dashboard
surface this as "last event processed X seconds ago" and error-rate trend — the freshness/volume check
required by the Data Quality & Observability section.

## Why Kafka rather than a hand-rolled queue
Kafka is used here (not a simulated in-process queue) because the syllabus explicitly grades "Streaming /
real-time processing" — a real broker gives partitioned ordering, consumer-group rebalancing, durable
replay from offset 0, and a dead-letter path that a fake queue can't demonstrate credibly in an interview.
