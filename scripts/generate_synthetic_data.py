"""
TravelOps 360 — Synthetic Data Generator
Generates a coherent, referentially-intact set of CSVs for:
  airports, aircraft, routes, customers, flights, bookings, baggage,
  fares, support tickets, and a date dimension.

Design goals:
  - Referential integrity (every FK resolves to a real PK)
  - Realistic operational patterns: delays cluster by airport/weather-proxy,
    cancellations cluster in bursts (to feed "cancellation cluster" rule),
    baggage SLA breaches correlate with delays,
    fares vary by days-to-departure (revenue mgmt curve),
    a "surge" week is injected for demand-surge alerting,
    load factor varies by route popularity.
  - Deterministic (seeded) so re-running reproduces the same dataset.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os

SEED = 42
rng = np.random.default_rng(SEED)
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. AIRPORTS
# ---------------------------------------------------------------------------
airports_raw = [
    ("BLR", "Bengaluru", "South", 55000),
    ("DEL", "Delhi", "North", 90000),
    ("BOM", "Mumbai", "West", 85000),
    ("MAA", "Chennai", "South", 40000),
    ("HYD", "Hyderabad", "South", 45000),
    ("CCU", "Kolkata", "East", 38000),
    ("GOI", "Goa", "West", 15000),
    ("PNQ", "Pune", "West", 22000),
    ("AMD", "Ahmedabad", "West", 20000),
    ("COK", "Kochi", "South", 18000),
    ("JAI", "Jaipur", "North", 14000),
    ("LKO", "Lucknow", "North", 13000),
    ("IXC", "Chandigarh", "North", 12000),
    ("VNS", "Varanasi", "North", 9000),
    ("GAU", "Guwahati", "East", 11000),
]
airports = pd.DataFrame(airports_raw, columns=["airport_id", "city", "region", "capacity"])
airports.to_csv(f"{OUT}/airports.csv", index=False)

# ---------------------------------------------------------------------------
# 2. AIRCRAFT
# ---------------------------------------------------------------------------
aircraft_types = [
    ("A320", 180), ("A321", 220), ("B737", 189), ("A20N", 186), ("B738", 175),
]
n_aircraft = 40
aircraft = pd.DataFrame({
    "aircraft_id": [f"AC{1000+i}" for i in range(n_aircraft)],
    "type": rng.choice([t for t, _ in aircraft_types], n_aircraft),
})
cap_map = dict(aircraft_types)
aircraft["seat_capacity"] = aircraft["type"].map(cap_map)
aircraft.to_csv(f"{OUT}/aircraft.csv", index=False)

# ---------------------------------------------------------------------------
# 3. ROUTES
# ---------------------------------------------------------------------------
airport_ids = airports["airport_id"].tolist()
routes = []
route_id = 1
for o in airport_ids:
    for d in airport_ids:
        if o == d:
            continue
        # not all pairs are flown — keep it realistic, hub-biased (DEL/BOM/BLR act as hubs)
        hubs = {"DEL", "BOM", "BLR"}
        if o in hubs or d in hubs or rng.random() < 0.15:
            routes.append((f"RT{route_id:04d}", o, d))
            route_id += 1
routes = pd.DataFrame(routes, columns=["route_id", "origin_airport_id", "dest_airport_id"])
# popularity score drives demand / load factor
routes["popularity"] = rng.gamma(shape=2.0, scale=1.0, size=len(routes))
routes.to_csv(f"{OUT}/routes.csv", index=False)

# ---------------------------------------------------------------------------
# 4. CUSTOMERS
# ---------------------------------------------------------------------------
n_customers = 6000
first_names = ["Aarav","Vivaan","Aditya","Ishaan","Ananya","Diya","Saanvi","Myra","Kabir","Reyansh",
               "Priya","Rahul","Neha","Karthik","Sneha","Arjun","Meera","Rohan","Kavya","Aditi"]
last_names = ["Sharma","Verma","Iyer","Nair","Reddy","Gupta","Singh","Patel","Menon","Das",
              "Rao","Kumar","Bose","Chatterjee","Pillai","Shetty","Joshi","Malhotra","Kapoor","Bansal"]
customers = pd.DataFrame({
    "customer_id": [f"CUST{100000+i}" for i in range(n_customers)],
    "name": [f"{rng.choice(first_names)} {rng.choice(last_names)}" for _ in range(n_customers)],
    "tier": rng.choice(["Standard", "Silver", "Gold", "Platinum"], n_customers, p=[0.6, 0.25, 0.1, 0.05]),
    "home_region": rng.choice(airports["region"].unique(), n_customers),
})
customers.to_csv(f"{OUT}/customers.csv", index=False)

# ---------------------------------------------------------------------------
# 5. DATE DIMENSION (90-day operating window, "today" = latest date)
# ---------------------------------------------------------------------------
END_DATE = datetime(2026, 9, 25)
START_DATE = END_DATE - timedelta(days=89)
dates = pd.date_range(START_DATE, END_DATE, freq="D")
dim_date = pd.DataFrame({
    "date_id": dates.strftime("%Y-%m-%d"),
    "date": dates,
    "year": dates.year, "month": dates.month, "day": dates.day,
    "day_of_week": dates.day_name(),
    "is_weekend": dates.dayofweek.isin([5, 6]),
})
dim_date.to_csv(f"{OUT}/dim_date.csv", index=False)

# Inject a demand-surge week and a cancellation-cluster event window
SURGE_START = START_DATE + timedelta(days=60)
SURGE_END = SURGE_START + timedelta(days=6)
CANCEL_CLUSTER_DATE = START_DATE + timedelta(days=75)  # e.g. simulated weather event at a hub

# ---------------------------------------------------------------------------
# 6. FLIGHTS
# ---------------------------------------------------------------------------
flights = []
flight_id = 1
route_ids = routes["route_id"].tolist()
route_pop = dict(zip(routes["route_id"], routes["popularity"]))
route_origin = dict(zip(routes["route_id"], routes["origin_airport_id"]))
aircraft_ids = aircraft["aircraft_id"].tolist()

for day in dates:
    is_surge = SURGE_START <= day <= SURGE_END
    n_flights_today = int(rng.integers(28, 40) * (1.3 if is_surge else 1.0))
    todays_routes = rng.choice(route_ids, size=n_flights_today,
                                p=(routes["popularity"] / routes["popularity"].sum()).values)
    for r in todays_routes:
        sched_hour = rng.integers(5, 23)
        sched_dep = day + timedelta(hours=int(sched_hour), minutes=int(rng.integers(0, 60)))
        origin = route_origin[r]
        # delay risk higher for congested hub airports and on the cancellation-cluster day
        hub_congestion = {"DEL": 0.22, "BOM": 0.20, "BLR": 0.15}.get(origin, 0.10)
        is_cluster_day = day.date() == CANCEL_CLUSTER_DATE.date()

        cancel_prob = 0.15 if is_cluster_day else 0.02
        status_roll = rng.random()
        if status_roll < cancel_prob:
            status = "CANCELLED"
            actual_dep = pd.NaT
            delay_min = np.nan
        else:
            status = "COMPLETED" if sched_dep < END_DATE - timedelta(hours=6) else rng.choice(
                ["COMPLETED", "SCHEDULED", "BOARDING", "DEPARTED"], p=[0.55, 0.25, 0.1, 0.1])
            # delay minutes: lognormal-ish, worse for congested hubs / cluster day
            base = rng.exponential(scale=8 + hub_congestion * 60)
            spike = 90 if is_cluster_day and rng.random() < 0.5 else 0
            delay_min = max(0, round(base + spike - 5))
            actual_dep = sched_dep + timedelta(minutes=int(delay_min)) if status != "SCHEDULED" else pd.NaT

        flights.append((
            f"FL{flight_id:06d}", r, rng.choice(aircraft_ids),
            sched_dep, actual_dep, status, round(float(delay_min), 1) if delay_min == delay_min else np.nan
        ))
        flight_id += 1

flights = pd.DataFrame(flights, columns=[
    "flight_id", "route_id", "aircraft_id", "scheduled_departure",
    "actual_departure", "status", "delay_minutes"
])
flights.to_csv(f"{OUT}/flights.csv", index=False)

# ---------------------------------------------------------------------------
# 7. FARES (time series per route/cabin as departure approaches — revenue mgmt curve)
# ---------------------------------------------------------------------------
fares = []
cabins = ["Economy", "PremiumEconomy", "Business"]
cabin_mult = {"Economy": 1.0, "PremiumEconomy": 1.6, "Business": 2.8}
for r in route_ids:
    base_price = 2500 + route_pop[r] * 1500 + rng.integers(-300, 300)
    for cabin in cabins:
        # 6 snapshots at decreasing days-to-departure, price rises as departure nears
        for days_out in [60, 30, 14, 7, 3, 1]:
            ts = END_DATE - timedelta(days=days_out)
            price = base_price * cabin_mult[cabin] * (1 + (60 - days_out) / 120) * (1 + rng.normal(0, 0.05))
            fares.append((r, cabin, ts, round(max(price, 800), 2)))
fares = pd.DataFrame(fares, columns=["route_id", "cabin", "timestamp", "price"])
fares.to_csv(f"{OUT}/fares.csv", index=False)

# ---------------------------------------------------------------------------
# 8. BOOKINGS (linked to flights; load factor driven by route popularity + surge)
# ---------------------------------------------------------------------------
bookings = []
booking_id = 1
aircraft_cap = dict(zip(aircraft["aircraft_id"], aircraft["seat_capacity"]))
customer_ids = customers["customer_id"].tolist()

for _, f in flights.iterrows():
    cap = aircraft_cap[f["aircraft_id"]]
    pop = route_pop[f["route_id"]]
    day_of_flight = f["scheduled_departure"]
    is_surge = SURGE_START <= day_of_flight <= SURGE_END
    target_load_factor = min(0.98, 0.45 + 0.08 * pop + (0.15 if is_surge else 0) + rng.normal(0, 0.05))
    target_load_factor = max(0.20, target_load_factor)
    n_book = int(cap * target_load_factor)

    for _ in range(n_book):
        cabin = rng.choice(cabins, p=[0.82, 0.12, 0.06])
        fare = cabin_mult[cabin] * (2500 + pop * 1500) * (1 + rng.normal(0, 0.1))
        booking_time = f["scheduled_departure"] - timedelta(days=int(rng.integers(1, 75)))
        if f["status"] == "CANCELLED":
            b_status = rng.choice(["REFUNDED", "REBOOKED"], p=[0.7, 0.3])
        else:
            b_status = rng.choice(["CONFIRMED", "CHECKED_IN", "COMPLETED"], p=[0.2, 0.2, 0.6])
        bookings.append((
            f"BK{booking_id:07d}", rng.choice(customer_ids), f["flight_id"],
            round(max(fare, 800), 2), booking_time, b_status
        ))
        booking_id += 1

bookings = pd.DataFrame(bookings, columns=[
    "booking_id", "customer_id", "flight_id", "fare", "booking_time", "status"
])
bookings.to_csv(f"{OUT}/bookings.csv", index=False)

# ---------------------------------------------------------------------------
# 9. BAGGAGE (one row per checked bag for a sample of bookings; SLA breach correlates with delay)
# ---------------------------------------------------------------------------
flight_delay = dict(zip(flights["flight_id"], flights["delay_minutes"]))
flight_origin_airport = dict(zip(flights["flight_id"], flights["route_id"].map(route_origin)))
flight_status = dict(zip(flights["flight_id"], flights["status"]))

baggage = []
bag_id = 1
checked_bookings = bookings[bookings["status"].isin(["CHECKED_IN", "COMPLETED"])]
# ~70% of eligible bookings check at least one bag
sample = checked_bookings.sample(frac=0.7, random_state=SEED)
for _, b in sample.iterrows():
    n_bags = rng.choice([1, 2], p=[0.75, 0.25])
    delay = flight_delay.get(b["flight_id"], 0)
    delay = 0 if pd.isna(delay) else delay
    for _ in range(n_bags):
        scan_time = b["booking_time"] + timedelta(hours=int(rng.integers(1, 48)))
        breach_prob = min(0.6, 0.03 + delay / 300)
        bag_status = "DELAYED" if rng.random() < breach_prob else rng.choice(
            ["LOADED", "DELIVERED", "IN_TRANSIT"], p=[0.3, 0.6, 0.1])
        baggage.append((
            f"BAG{bag_id:07d}", b["booking_id"], scan_time,
            flight_origin_airport.get(b["flight_id"], rng.choice(airport_ids)), bag_status
        ))
        bag_id += 1
baggage = pd.DataFrame(baggage, columns=["bag_id", "booking_id", "scan_time", "airport", "status"])
baggage.to_csv(f"{OUT}/baggage.csv", index=False)

# ---------------------------------------------------------------------------
# 10. SUPPORT TICKETS (complaints correlate with delay/cancellation/baggage issues)
# ---------------------------------------------------------------------------
bag_issue_bookings = set(baggage[baggage["status"] == "DELAYED"]["booking_id"])
cancelled_flight_ids = set(flights[flights["status"] == "CANCELLED"]["flight_id"])
cancelled_bookings = set(bookings[bookings["flight_id"].isin(cancelled_flight_ids)]["booking_id"])

support = []
ticket_id = 1
issue_types = ["DELAY_COMPLAINT", "BAGGAGE_ISSUE", "CANCELLATION", "REFUND_REQUEST", "SERVICE_QUALITY"]

for _, b in bookings.iterrows():
    p_ticket = 0.03
    forced_issue = None
    if b["booking_id"] in cancelled_bookings:
        p_ticket = 0.55
        forced_issue = "CANCELLATION"
    elif b["booking_id"] in bag_issue_bookings:
        p_ticket = 0.45
        forced_issue = "BAGGAGE_ISSUE"
    else:
        delay = flight_delay.get(b["flight_id"], 0)
        delay = 0 if pd.isna(delay) else delay
        if delay > 45:
            p_ticket = 0.35
            forced_issue = "DELAY_COMPLAINT"

    if rng.random() < p_ticket:
        issue = forced_issue if forced_issue else rng.choice(issue_types)
        created_at = b["booking_time"] + timedelta(days=int(rng.integers(0, 5)))
        support.append((f"TCK{ticket_id:06d}", b["booking_id"], issue, created_at))
        ticket_id += 1

support = pd.DataFrame(support, columns=["ticket_id", "booking_id", "issue_type", "created_at"])
support.to_csv(f"{OUT}/support_tickets.csv", index=False)

# ---------------------------------------------------------------------------
# 10b. DELIBERATE DATA-QUALITY ISSUES (so the Silver validation layer has
#      real defects to catch and report — mirrors real-world messy sources)
# ---------------------------------------------------------------------------
def inject_dirty_rows(df, pk_col, frac_null=0.003, frac_dup=0.002, frac_bad_fk=0.0, fk_col=None):
    df = df.copy()
    n = len(df)
    # null out some PKs
    null_idx = rng.choice(df.index, size=int(n * frac_null), replace=False)
    df.loc[null_idx, pk_col] = np.nan
    # duplicate some PKs (copy a row's PK onto another row)
    dup_idx = rng.choice(df.index, size=int(n * frac_dup), replace=False)
    shuffled_pks = df[pk_col].sample(frac=1.0, random_state=1).values
    df.loc[dup_idx, pk_col] = shuffled_pks[: len(dup_idx)]
    # bad foreign keys pointing to nothing
    if fk_col and frac_bad_fk > 0:
        bad_fk_idx = rng.choice(df.index, size=int(n * frac_bad_fk), replace=False)
        df.loc[bad_fk_idx, fk_col] = ["UNKNOWN_REF_" + str(i) for i in bad_fk_idx]
    return df

flights = inject_dirty_rows(flights, "flight_id", frac_null=0.002, frac_dup=0.002,
                             frac_bad_fk=0.003, fk_col="aircraft_id")
bookings = inject_dirty_rows(bookings, "booking_id", frac_null=0.001, frac_dup=0.001,
                              frac_bad_fk=0.003, fk_col="flight_id")
baggage = inject_dirty_rows(baggage, "bag_id", frac_null=0.002, frac_dup=0.001,
                             frac_bad_fk=0.002, fk_col="booking_id")
# a few negative/zero fares and out-of-range delay values (business-rule violations)
neg_fare_idx = rng.choice(bookings.index, size=max(1, int(len(bookings) * 0.0005)), replace=False)
bookings.loc[neg_fare_idx, "fare"] = -rng.integers(100, 500, size=len(neg_fare_idx))
bad_delay_idx = rng.choice(flights.index, size=max(1, int(len(flights) * 0.001)), replace=False)
flights.loc[bad_delay_idx, "delay_minutes"] = -rng.integers(1, 20, size=len(bad_delay_idx))

# re-write the now-dirtied CSVs (overwrite earlier clean writes)
flights.to_csv(f"{OUT}/flights.csv", index=False)
bookings.to_csv(f"{OUT}/bookings.csv", index=False)
baggage.to_csv(f"{OUT}/baggage.csv", index=False)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("Synthetic data generated:")
for name, df in [
    ("airports", airports), ("aircraft", aircraft), ("routes", routes),
    ("customers", customers), ("dim_date", dim_date), ("flights", flights),
    ("fares", fares), ("bookings", bookings), ("baggage", baggage),
    ("support_tickets", support),
]:
    print(f"  {name:16s} {len(df):>8,d} rows")

print(f"\nSurge window   : {SURGE_START.date()} -> {SURGE_END.date()}")
print(f"Cancel cluster : {CANCEL_CLUSTER_DATE.date()}")
print(f"Date window    : {START_DATE.date()} -> {END_DATE.date()}")
