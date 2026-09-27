"""
TravelOps 360 — Data Quality Check Runner
Executes the categories from sql/dq_checks.sql as discrete, logged checks against
the DuckDB warehouse. Writes results to travelops.dq_check_log and exits non-zero
if any check fails (so this can gate an orchestration pipeline).

Run: python3 scripts/run_dq_checks.py
"""
import duckdb
import os
import sys
import uuid
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(ROOT, "data", "warehouse", "travelops.duckdb")
BATCH_ID = str(uuid.uuid4())[:8]

con = duckdb.connect(DB_PATH)
con.execute("SET SCHEMA 'travelops'")

CHECKS = [
    # (name, sql returning a single 'violations' count, threshold)
    ("null_pk_fact_flight", "SELECT count(*) FROM fact_flight WHERE flight_id IS NULL", 0),
    ("null_pk_fact_booking", "SELECT count(*) FROM fact_booking WHERE booking_id IS NULL", 0),
    ("dup_pk_fact_flight",
     "SELECT count(*) FROM (SELECT flight_id FROM fact_flight GROUP BY flight_id HAVING count(*) > 1)", 0),
    ("dup_pk_fact_booking",
     "SELECT count(*) FROM (SELECT booking_id FROM fact_booking GROUP BY booking_id HAVING count(*) > 1)", 0),
    ("ref_integrity_booking_to_flight",
     "SELECT count(*) FROM fact_booking b LEFT JOIN fact_flight f ON b.flight_id = f.flight_id WHERE f.flight_id IS NULL", 0),
    ("ref_integrity_booking_to_customer",
     "SELECT count(*) FROM fact_booking b LEFT JOIN dim_customer c ON b.customer_id = c.customer_id WHERE c.customer_id IS NULL", 0),
    ("ref_integrity_baggage_to_booking",
     "SELECT count(*) FROM fact_baggage g LEFT JOIN fact_booking b ON g.booking_id = b.booking_id WHERE b.booking_id IS NULL", 0),
    ("ref_integrity_support_to_booking",
     "SELECT count(*) FROM fact_support_ticket s LEFT JOIN fact_booking b ON s.booking_id = b.booking_id WHERE b.booking_id IS NULL", 0),
    ("ref_integrity_flight_to_route",
     "SELECT count(*) FROM fact_flight f LEFT JOIN dim_route r ON f.route_id = r.route_id WHERE r.route_id IS NULL", 0),
    ("range_delay_minutes_negative", "SELECT count(*) FROM fact_flight WHERE delay_minutes < 0", 0),
    ("range_fare_non_positive", "SELECT count(*) FROM fact_booking WHERE fare <= 0", 0),
    ("range_fare_snapshot_price_non_positive", "SELECT count(*) FROM fact_fare_snapshot WHERE price <= 0", 0),
    ("valid_flight_status",
     "SELECT count(*) FROM fact_flight WHERE status NOT IN ('SCHEDULED','BOARDING','DEPARTED','COMPLETED','CANCELLED')", 0),
]

# Streaming checks are appended only if the streaming module has run at least once
# (fact_flight_status_live etc. are created lazily by streaming/consumer.py).
existing_tables = set(con.sql(
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'travelops'"
).df()["table_name"])

if "stream_monitoring" in existing_tables:
    CHECKS += [
        ("stream_freshness_minutes_ok",
         "SELECT CASE WHEN date_diff('minute', max(window_end), now()) > 30 THEN 1 ELSE 0 END "
         "FROM stream_monitoring", 0),
        ("stream_error_rate_ok",
         "SELECT CASE WHEN sum(errors) > 0.05 * sum(processed + duplicates + errors) THEN 1 ELSE 0 END "
         "FROM stream_monitoring", 0),
    ]
if "stream_seen_events" in existing_tables:
    CHECKS.append((
        "stream_dedup_ledger_unique",
        "SELECT count(*) FROM (SELECT event_id FROM stream_seen_events GROUP BY event_id HAVING count(*) > 1)", 0,
    ))

print(f"Running {len(CHECKS)} data-quality checks  |  batch={BATCH_ID}\n")

failures = []
for name, sql, threshold in CHECKS:
    violations = con.sql(sql).fetchone()[0]
    status = "PASS" if violations <= threshold else "FAIL"
    if status == "FAIL":
        failures.append(name)
    con.execute(
        "INSERT INTO dq_check_log VALUES (?,?,?,?,?,?,?)",
        [str(uuid.uuid4())[:8], name, "warehouse", status, f"violations={violations}",
         datetime.now(timezone.utc), BATCH_ID],
    )
    mark = "✅" if status == "PASS" else "❌"
    print(f"  {mark} {name:42s} {status}  (violations={violations})")

# freshness check
hours = con.sql("SELECT date_diff('hour', max(_ingested_at), now()) FROM fact_flight").fetchone()[0]
fresh_status = "PASS" if hours is not None and hours < 24 else "FAIL"
if fresh_status == "FAIL":
    failures.append("freshness_fact_flight")
con.execute(
    "INSERT INTO dq_check_log VALUES (?,?,?,?,?,?,?)",
    [str(uuid.uuid4())[:8], "freshness_fact_flight", "warehouse", fresh_status,
     f"hours_since_load={hours}", datetime.now(timezone.utc), BATCH_ID],
)
print(f"  {'✅' if fresh_status=='PASS' else '❌'} {'freshness_fact_flight':42s} {fresh_status}  (hours_since_load={hours})")

# volume anomaly (informational — logs LOW_VOLUME_ALERT days, doesn't fail the pipeline)
low_volume_days = con.sql("""
    WITH daily AS (
        SELECT scheduled_date_id, count(*) AS n_flights FROM fact_flight GROUP BY scheduled_date_id
    )
    SELECT scheduled_date_id, n_flights FROM daily
    WHERE n_flights < 0.3 * (SELECT avg(n_flights) FROM daily)
""").df()
if len(low_volume_days):
    print(f"\n  ⚠️  Volume anomaly: {len(low_volume_days)} day(s) with unusually low flight counts:")
    print(low_volume_days.to_string(index=False))

con.close()

print(f"\n{len(CHECKS)+1 - len(failures)}/{len(CHECKS)+1} checks passed.")
if failures:
    print(f"FAILED CHECKS: {failures}")
    sys.exit(1)
else:
    print("All data-quality checks passed.")
