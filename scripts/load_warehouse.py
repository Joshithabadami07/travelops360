"""
TravelOps 360 — Silver -> Warehouse (DuckDB)
Creates the star schema (first run) and incrementally UPSERTs from the Silver
parquet layer using each table's business/primary key (idempotent — safe to re-run).

Run:
  python3 scripts/load_warehouse.py            # incremental upsert (creates schema if missing)
  python3 scripts/load_warehouse.py --rebuild   # drop & recreate schema from scratch, then load
"""
import duckdb
import pandas as pd
import os
import sys
import uuid
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
SILVER = os.path.join(ROOT, "data", "silver")
WAREHOUSE_DIR = os.path.join(ROOT, "data", "warehouse")
os.makedirs(WAREHOUSE_DIR, exist_ok=True)
DB_PATH = os.path.join(WAREHOUSE_DIR, "travelops.duckdb")
SCHEMA_SQL = os.path.join(ROOT, "sql", "schema.sql")

RUN_ID = str(uuid.uuid4())[:8]
REBUILD = "--rebuild" in sys.argv

con = duckdb.connect(DB_PATH)

schema_exists = con.sql(
    "SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'travelops'"
).fetchone()[0] > 0

if REBUILD or not schema_exists:
    print("Building schema (travelops.*) ...")
    with open(SCHEMA_SQL) as f:
        con.execute(f.read())
else:
    con.execute("SET SCHEMA 'travelops'")

UPSERT_COLS_CACHE = {}


def upsert(table: str, df: pd.DataFrame, pk_cols: list[str], task_name: str):
    started = datetime.now(timezone.utc)
    if df.empty:
        con.execute(
            "INSERT INTO pipeline_run_log VALUES (?,?,?,?,?,?,?)",
            [RUN_ID, task_name, "SUCCESS", 0, started, datetime.now(timezone.utc), "no rows"],
        )
        print(f"  {table:24s} 0 rows (empty input)")
        return
    con.register("stg_df", df)
    cols = list(df.columns)
    col_list = ", ".join(cols)
    update_cols = [c for c in cols if c not in pk_cols]
    join_clause = " AND ".join([f"t.{c} = stg.{c}" for c in pk_cols])
    try:
        # UPDATE existing rows in place (avoids DuckDB's delete+insert-on-conflict,
        # which trips FK constraints when the row is referenced elsewhere).
        if update_cols:
            set_clause = ", ".join([f"{c} = stg.{c}" for c in update_cols])
            con.execute(f"""
                UPDATE {table} AS t SET {set_clause}
                FROM stg_df AS stg
                WHERE {join_clause}
            """)
        # INSERT genuinely new rows only.
        anti_join = " AND ".join([f"t.{c} = stg.{c}" for c in pk_cols])
        con.execute(f"""
            INSERT INTO {table} ({col_list})
            SELECT {col_list} FROM stg_df AS stg
            WHERE NOT EXISTS (SELECT 1 FROM {table} AS t WHERE {anti_join})
        """)
        ended = datetime.now(timezone.utc)
        con.execute(
            "INSERT INTO pipeline_run_log VALUES (?,?,?,?,?,?,?)",
            [RUN_ID, task_name, "SUCCESS", len(df), started, ended, None],
        )
        print(f"  {table:24s} {len(df):>8,d} rows upserted")
    except Exception as e:
        ended = datetime.now(timezone.utc)
        con.execute(
            "INSERT INTO pipeline_run_log VALUES (?,?,?,?,?,?,?)",
            [RUN_ID, task_name, "FAILED", 0, started, ended, str(e)[:500]],
        )
        print(f"  {table:24s} FAILED: {e}")
        raise
    finally:
        con.unregister("stg_df")


print(f"Run: {RUN_ID}  |  {DB_PATH}\n")
print("Loading dimensions...")

dim_airport = pd.read_parquet(f"{SILVER}/airports.parquet").rename(columns={}).drop(columns=["_is_valid"])
upsert("dim_airport", dim_airport[["airport_id", "city", "region", "capacity",
                                    "_source_file", "_batch_id", "_ingested_at"]], ["airport_id"], "load_dim_airport")

dim_aircraft = pd.read_parquet(f"{SILVER}/aircraft.parquet").drop(columns=["_is_valid"])
upsert("dim_aircraft", dim_aircraft[["aircraft_id", "type", "seat_capacity",
                                      "_source_file", "_batch_id", "_ingested_at"]], ["aircraft_id"], "load_dim_aircraft")

dim_customer = pd.read_parquet(f"{SILVER}/customers.parquet").drop(columns=["_is_valid"])
upsert("dim_customer", dim_customer[["customer_id", "name", "tier", "home_region",
                                      "_source_file", "_batch_id", "_ingested_at"]], ["customer_id"], "load_dim_customer")

dim_date = pd.read_parquet(f"{SILVER}/dim_date.parquet").drop(columns=["_is_valid"])
upsert("dim_date", dim_date[["date_id", "date", "year", "month", "day", "day_of_week", "is_weekend",
                              "_source_file", "_batch_id", "_ingested_at"]], ["date_id"], "load_dim_date")

dim_route = pd.read_parquet(f"{SILVER}/routes.parquet").drop(columns=["_is_valid"])
upsert("dim_route", dim_route[["route_id", "origin_airport_id", "dest_airport_id", "popularity",
                                "_source_file", "_batch_id", "_ingested_at"]], ["route_id"], "load_dim_route")

print("\nLoading facts...")

flights = pd.read_parquet(f"{SILVER}/flights.parquet").drop(columns=["_is_valid"])
flights["scheduled_date_id"] = pd.to_datetime(flights["scheduled_departure"]).dt.strftime("%Y-%m-%d")
upsert("fact_flight", flights[["flight_id", "route_id", "aircraft_id", "scheduled_date_id",
                                "scheduled_departure", "actual_departure", "status", "delay_minutes",
                                "_source_file", "_batch_id", "_ingested_at"]], ["flight_id"], "load_fact_flight")

cancellations = pd.read_parquet(f"{SILVER}/cancellations.parquet")
upsert("fact_cancellation", cancellations[["flight_id", "cancelled_at", "reason_code",
                                            "_source_file", "_batch_id", "_ingested_at"]], ["flight_id"], "load_fact_cancellation")

bookings = pd.read_parquet(f"{SILVER}/bookings.parquet").drop(columns=["_is_valid"])
upsert("fact_booking", bookings[["booking_id", "customer_id", "flight_id", "fare", "booking_time", "status",
                                  "_source_file", "_batch_id", "_ingested_at"]], ["booking_id"], "load_fact_booking")

baggage = pd.read_parquet(f"{SILVER}/baggage.parquet").drop(columns=["_is_valid"])
upsert("fact_baggage", baggage[["bag_id", "booking_id", "scan_time", "airport", "status",
                                 "_source_file", "_batch_id", "_ingested_at"]], ["bag_id"], "load_fact_baggage")

support = pd.read_parquet(f"{SILVER}/support_tickets.parquet").drop(columns=["_is_valid"])
upsert("fact_support_ticket", support[["ticket_id", "booking_id", "issue_type", "created_at",
                                        "_source_file", "_batch_id", "_ingested_at"]], ["ticket_id"], "load_fact_support_ticket")

fares = pd.read_parquet(f"{SILVER}/fares.parquet")
if "_is_valid" in fares.columns:
    fares = fares.drop(columns=["_is_valid"])
upsert("fact_fare_snapshot", fares[["route_id", "cabin", "timestamp", "price",
                                     "_source_file", "_batch_id", "_ingested_at"]], ["route_id", "cabin", "timestamp"], "load_fact_fare_snapshot")

print("\nWarehouse tables (exact counts):")
table_names = con.sql("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'travelops' ORDER BY table_name
""").df()["table_name"].tolist()
for t in table_names:
    n = con.sql(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t:24s} {n:>9,d} rows")

con.close()
print(f"\nWarehouse ready at: {DB_PATH}")
