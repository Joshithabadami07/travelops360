"""
TravelOps 360 — Bronze -> Silver
Cleansing, schema validation, deduplication, audit columns, business-key checks.

Run: python3 scripts/silver_transform.py
Output: data/silver/*.parquet  (+ data/silver/_rejects/*.csv for rows that fail validation)
"""
import pandas as pd
import numpy as np
import os
import uuid
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
BRONZE = os.path.join(ROOT, "data", "bronze")
SILVER = os.path.join(ROOT, "data", "silver")
REJECTS = os.path.join(SILVER, "_rejects")
os.makedirs(SILVER, exist_ok=True)
os.makedirs(REJECTS, exist_ok=True)

BATCH_ID = str(uuid.uuid4())[:8]
INGESTED_AT = datetime.now(timezone.utc).isoformat()


def add_audit_columns(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    df = df.copy()
    df["_source_file"] = source_file
    df["_batch_id"] = BATCH_ID
    df["_ingested_at"] = INGESTED_AT
    return df


def validate_and_split(df: pd.DataFrame, pk_cols, not_null_cols, name: str):
    """Return (valid_df, rejected_df) based on PK null/dup + not-null business rules."""
    df = df.copy()
    reasons = pd.Series([""] * len(df), index=df.index)

    # PK null check
    pk_null_mask = df[pk_cols].isnull().any(axis=1)
    reasons[pk_null_mask] += "pk_null;"

    # not-null business fields
    for col in not_null_cols:
        if col in df.columns:
            mask = df[col].isnull()
            reasons[mask] += f"{col}_null;"

    # duplicate PK (keep first, flag rest)
    dup_mask = df.duplicated(subset=pk_cols, keep="first")
    reasons[dup_mask] += "duplicate_pk;"

    is_invalid = reasons != ""
    valid_df = df[~is_invalid].copy()
    rejected_df = df[is_invalid].copy()
    rejected_df["_reject_reason"] = reasons[is_invalid]

    valid_df["_is_valid"] = True
    if len(rejected_df):
        rejected_df.to_csv(f"{REJECTS}/{name}_rejects.csv", index=False)
    return valid_df, rejected_df


def report(name, raw_n, valid_n, rejected_n):
    print(f"  {name:18s} raw={raw_n:>8,d}  valid={valid_n:>8,d}  rejected={rejected_n:>6,d}")


print(f"Batch: {BATCH_ID}  |  Silver cleansing run at {INGESTED_AT}\n")

# ---------------------------------------------------------------------------
# Dimension sources (SCD-1 : simple overwrite-on-change, deduped by PK)
# ---------------------------------------------------------------------------
airports = pd.read_csv(f"{BRONZE}/airports.csv")
airports_v, airports_r = validate_and_split(airports, ["airport_id"], ["city", "region"], "airports")
airports_v = add_audit_columns(airports_v, "airports.csv")
airports_v.to_parquet(f"{SILVER}/airports.parquet", index=False)
report("airports", len(airports), len(airports_v), len(airports_r))

aircraft = pd.read_csv(f"{BRONZE}/aircraft.csv")
aircraft_v, aircraft_r = validate_and_split(aircraft, ["aircraft_id"], ["type", "seat_capacity"], "aircraft")
aircraft_v = add_audit_columns(aircraft_v, "aircraft.csv")
aircraft_v.to_parquet(f"{SILVER}/aircraft.parquet", index=False)
report("aircraft", len(aircraft), len(aircraft_v), len(aircraft_r))

routes = pd.read_csv(f"{BRONZE}/routes.csv")
# referential integrity: origin/dest must exist in airports
valid_airport_ids = set(airports_v["airport_id"])
ref_ok = routes["origin_airport_id"].isin(valid_airport_ids) & routes["dest_airport_id"].isin(valid_airport_ids)
routes_ref_bad = routes[~ref_ok]
routes = routes[ref_ok]
routes_v, routes_r = validate_and_split(routes, ["route_id"], ["origin_airport_id", "dest_airport_id"], "routes")
routes_v = add_audit_columns(routes_v, "routes.csv")
routes_v.to_parquet(f"{SILVER}/routes.parquet", index=False)
report("routes", len(routes) + len(routes_ref_bad), len(routes_v), len(routes_r) + len(routes_ref_bad))

customers = pd.read_csv(f"{BRONZE}/customers.csv")
customers_v, customers_r = validate_and_split(customers, ["customer_id"], ["name"], "customers")
customers_v = add_audit_columns(customers_v, "customers.csv")
customers_v.to_parquet(f"{SILVER}/customers.parquet", index=False)
report("customers", len(customers), len(customers_v), len(customers_r))

dim_date = pd.read_csv(f"{BRONZE}/dim_date.csv")
dim_date_v, dim_date_r = validate_and_split(dim_date, ["date_id"], ["date"], "dim_date")
dim_date_v = add_audit_columns(dim_date_v, "dim_date.csv")
dim_date_v.to_parquet(f"{SILVER}/dim_date.parquet", index=False)
report("dim_date", len(dim_date), len(dim_date_v), len(dim_date_r))

# ---------------------------------------------------------------------------
# Flights (fact) — business rules: scheduled_departure required; status in valid set;
# delay_minutes must be >= 0 when present; referential integrity to route/aircraft
# ---------------------------------------------------------------------------
flights = pd.read_csv(f"{BRONZE}/flights.csv", parse_dates=["scheduled_departure", "actual_departure"])
valid_route_ids = set(routes_v["route_id"])
valid_aircraft_ids = set(aircraft_v["aircraft_id"])
valid_status = {"SCHEDULED", "BOARDING", "DEPARTED", "COMPLETED", "CANCELLED"}

ref_ok = flights["route_id"].isin(valid_route_ids) & flights["aircraft_id"].isin(valid_aircraft_ids)
range_ok = flights["status"].isin(valid_status) & (flights["delay_minutes"].isna() | (flights["delay_minutes"] >= 0))
flights_bad_business = flights[~(ref_ok & range_ok)]
flights_ok = flights[ref_ok & range_ok]

flights_v, flights_r = validate_and_split(flights_ok, ["flight_id"], ["route_id", "scheduled_departure"], "flights")
flights_v = add_audit_columns(flights_v, "flights.csv")
flights_v.to_parquet(f"{SILVER}/flights.parquet", index=False)
report("flights", len(flights), len(flights_v), len(flights_r) + len(flights_bad_business))

# Derived: cancellations fact
cancellations = flights_v[flights_v["status"] == "CANCELLED"][["flight_id", "scheduled_departure"]].copy()
cancellations = cancellations.rename(columns={"scheduled_departure": "cancelled_at"})
cancellations["reason_code"] = "UNSPECIFIED"  # placeholder — spec doesn't provide a reason field in source
cancellations = add_audit_columns(cancellations, "derived:flights.csv")
cancellations.to_parquet(f"{SILVER}/cancellations.parquet", index=False)
print(f"  {'cancellations':18s} derived={len(cancellations):>8,d} (from CANCELLED flights)")

# ---------------------------------------------------------------------------
# Bookings (fact) — referential integrity to customer/flight; fare must be > 0
# ---------------------------------------------------------------------------
bookings = pd.read_csv(f"{BRONZE}/bookings.csv", parse_dates=["booking_time"])
valid_customer_ids = set(customers_v["customer_id"])
valid_flight_ids = set(flights_v["flight_id"])

ref_ok = bookings["customer_id"].isin(valid_customer_ids) & bookings["flight_id"].isin(valid_flight_ids)
range_ok = bookings["fare"] > 0
bookings_bad_business = bookings[~(ref_ok & range_ok)]
bookings_ok = bookings[ref_ok & range_ok]

bookings_v, bookings_r = validate_and_split(bookings_ok, ["booking_id"], ["customer_id", "flight_id", "fare"], "bookings")
bookings_v = add_audit_columns(bookings_v, "bookings.csv")
bookings_v.to_parquet(f"{SILVER}/bookings.parquet", index=False)
report("bookings", len(bookings), len(bookings_v), len(bookings_r) + len(bookings_bad_business))

# ---------------------------------------------------------------------------
# Baggage (fact) — referential integrity to booking + airport
# ---------------------------------------------------------------------------
baggage = pd.read_csv(f"{BRONZE}/baggage.csv", parse_dates=["scan_time"])
valid_booking_ids = set(bookings_v["booking_id"])
ref_ok = baggage["booking_id"].isin(valid_booking_ids) & baggage["airport"].isin(valid_airport_ids)
baggage_bad_business = baggage[~ref_ok]
baggage_ok = baggage[ref_ok]

baggage_v, baggage_r = validate_and_split(baggage_ok, ["bag_id"], ["booking_id", "status"], "baggage")
baggage_v = add_audit_columns(baggage_v, "baggage.csv")
baggage_v.to_parquet(f"{SILVER}/baggage.parquet", index=False)
report("baggage", len(baggage), len(baggage_v), len(baggage_r) + len(baggage_bad_business))

# ---------------------------------------------------------------------------
# Support tickets (fact) — referential integrity to booking
# ---------------------------------------------------------------------------
support = pd.read_csv(f"{BRONZE}/support_tickets.csv", parse_dates=["created_at"])
ref_ok = support["booking_id"].isin(valid_booking_ids)
support_bad_business = support[~ref_ok]
support_ok = support[ref_ok]

support_v, support_r = validate_and_split(support_ok, ["ticket_id"], ["booking_id", "issue_type"], "support_tickets")
support_v = add_audit_columns(support_v, "support_tickets.csv")
support_v.to_parquet(f"{SILVER}/support_tickets.parquet", index=False)
report("support_tickets", len(support), len(support_v), len(support_r) + len(support_bad_business))

# ---------------------------------------------------------------------------
# Fares (fact) — price must be > 0; referential integrity to route
# ---------------------------------------------------------------------------
fares = pd.read_csv(f"{BRONZE}/fares.csv", parse_dates=["timestamp"])
ref_ok = fares["route_id"].isin(valid_route_ids)
range_ok = fares["price"] > 0
fares_bad_business = fares[~(ref_ok & range_ok)]
fares_ok = fares[ref_ok & range_ok]
fares_v = add_audit_columns(fares_ok, "fares.csv")
fares_v["_is_valid"] = True
fares_v.to_parquet(f"{SILVER}/fares.parquet", index=False)
report("fares", len(fares), len(fares_v), len(fares_bad_business))

print(f"\nSilver layer written to: {SILVER}")
print(f"Rejected rows (if any) written to: {REJECTS}")
