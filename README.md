# TravelOps 360 — Airline/Travel Operations & Revenue Analytics Platform

End-to-end capstone: bookings, flight status, baggage, cancellations, airport ops and fares →
governed warehouse → analytics/ML → automated decisions → API → frontend.

## Status vs. the 6-week plan

| Week | Deliverable | Status |
|---|---|---|
| 1 | Business analysis, dataset, architecture, ERD, GitHub setup | ✅ Done |
| 2 | Ingestion, Bronze/Silver, warehouse + dimensional model | ✅ Done (this commit) |
| 3 | Kafka streaming, PySpark job, dbt marts, DQ tests | ✅ Done (this commit) |
| 4 | Analytics layer, ML/forecast/risk models, automation engine | ⬜ Next |
| 5 | FastAPI, frontend, auth, roles, integration | ⬜ |
| 6 | Cloud deployment, Docker, CI/CD, testing, docs, demo | ⬜ |

## Week 3 additions
```
streaming/
├── docker-compose.yml      # single-broker Kafka (KRaft) + Kafka UI
├── create_topics.sh
├── producer.py              # replays Silver events live, injects dup/out-of-order for proof
├── consumer.py               # dedup + out-of-order-safe + retry + dead-letter + monitoring
└── README.md                 # retry / dedup / out-of-order / monitoring write-up
spark/
├── rotation_delay_propagation.py        # PySpark: aircraft rotation & delay-cascade analysis
└── load_rotation_mart_to_warehouse.py    # loads Spark's parquet output into DuckDB
dbt_project/
├── models/staging/    # thin views over the warehouse's dim_*/fact_* tables, + schema tests
└── models/marts/      # the 7 required KPI marts, each with a business-action writeup
```
Run order for week 3 (after week 1-2's pipeline has been run at least once):
```bash
pip install -r requirements.txt
docker compose -f streaming/docker-compose.yml up -d && ./streaming/create_topics.sh
python3 streaming/consumer.py &                 # start processor first
python3 streaming/producer.py --speed 500        # replay live events

python3 spark/rotation_delay_propagation.py
python3 spark/load_rotation_mart_to_warehouse.py

cp dbt_project/profiles.yml.example ~/.dbt/profiles.yml   # once
cd dbt_project && dbt run && dbt test
```

## Repo layout so far
```
travelops360/
├── data/
│   ├── bronze/          # synthetic raw source data (immutable)
│   ├── silver/          # cleansed, validated, audit-columned (+ _rejects/ for bad rows)
│   └── warehouse/       # travelops.duckdb — the star-schema warehouse
├── docs/
│   ├── architecture.md       # architecture + orchestration diagrams
│   ├── erd.md                 # star schema ERD
│   ├── data_dictionary.md
│   └── recovery_procedure.md # what to do when a pipeline step fails
├── sql/
│   ├── schema.sql       # warehouse DDL (dims + facts + audit/log tables)
│   └── dq_checks.sql    # data-quality checks, as plain SQL
├── scripts/
│   ├── generate_synthetic_data.py  # Bronze
│   ├── silver_transform.py         # Bronze -> Silver (validation, dedup, rejects)
│   ├── load_warehouse.py           # Silver -> DuckDB warehouse (idempotent upsert)
│   └── run_dq_checks.py            # runs sql/dq_checks.sql, logs to dq_check_log
```

## What's in the Bronze layer
Referentially-intact synthetic data for a 90-day operating window (2026-06-28 → 2026-09-25):
- 15 airports, 40 aircraft, 98 routes, 6,000 customers
- 3,082 flights, ~415K bookings, ~285K baggage scans, ~30K support tickets, fare snapshots per route/cabin
- A **demand-surge week** (2026-08-27 → 2026-09-02) and a **cancellation-cluster day** (2026-09-11) are
  deliberately injected so the automation-rule and anomaly-detection modules have real signal to catch later.
- A small % of rows are **deliberately dirty** (null/duplicate PKs, bad foreign keys, negative fares/delays)
  so the Silver validation layer has real defects to catch — see the reject counts below.

## Pipeline: Bronze -> Silver -> Warehouse -> DQ checks
Run in order (each step is idempotent / safe to re-run):
```bash
python3 scripts/generate_synthetic_data.py   # writes data/bronze/*.csv
python3 scripts/silver_transform.py          # writes data/silver/*.parquet + _rejects/
python3 scripts/load_warehouse.py            # builds/loads data/warehouse/travelops.duckdb
python3 scripts/run_dq_checks.py             # runs sql/dq_checks.sql, exits non-zero on failure
```

Latest run caught real defects at Silver (proof the validation layer works) and the warehouse
still passed all 14 downstream DQ checks, because the bad rows never made it past Silver:

| Table | Bronze rows | Silver-valid | Rejected |
|---|---:|---:|---:|
| flights | 3,082 | 3,058 | 24 |
| bookings | 414,870 | 409,345 | 5,525 |
| baggage | 284,642 | 279,399 | 5,243 |
| support_tickets | 30,127 | 29,804 | 323 |

## Next step
Week 3: Kafka-equivalent streaming (live flight status / baggage scan / booking event topics),
PySpark-or-pandas stream processing, dbt marts on top of the warehouse, and the automated
data-quality test suite wired into an Airflow-shaped DAG.
