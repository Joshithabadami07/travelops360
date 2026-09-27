# TravelOps 360 — Architecture

## Technology mapping (spec technology -> equivalent used in this build)

| Spec asks for | We use | Why |
|---|---|---|
| Kafka | `confluent-kafka`/`aiokafka` compatible **local event-log broker** (topic/partition/offset/consumer-group semantics implemented over SQLite + append-only files) OR real Kafka via `docker-compose` (bitnami/kafka) when Docker is available | Same pub/sub + consumer-group + offset semantics as Kafka; swappable for a real broker by changing one config value |
| GCS/S3 | Local `data/bronze` (immutable, partitioned by `_batch_id`/date) | Same "raw immutable zone" pattern; swap for a boto3/gcsfs client later |
| BigQuery/Snowflake | **DuckDB** (`data/warehouse/travelops.duckdb`) | Full SQL warehouse semantics (dbt-duckdb adapter exists), zero-cost, runs anywhere |
| dbt | `dbt-duckdb` project | Real dbt: staging -> intermediate -> marts, tests, docs |
| Airflow | Real Airflow **DAG definitions** (`orchestration/dags/`) + a lightweight local runner script that executes the same DAG shape for demo without needing the Airflow webserver | DAG code is portable to a real Airflow deployment unchanged |
| FastAPI | FastAPI | Direct match |
| React/Next.js | React/Next.js frontend (or a published single-page app artifact for the live demo) | Direct match |
| Docker/GitHub Actions | Dockerfiles per service + `.github/workflows/ci.yml` | Direct match |
| Cloud deployment | Deployment docs for Render/Fly.io/AWS (free-tier friendly) | Direct match, documented step by step |

## End-to-end flow

```mermaid
flowchart LR
    subgraph Sources
        A1[Bookings events]
        A2[Flight status events]
        A3[Baggage scan events]
    end

    subgraph Streaming["Event Bus (Kafka-equivalent)"]
        K1[(topic: flight_status)]
        K2[(topic: baggage_scan)]
        K3[(topic: booking_events)]
    end

    subgraph Lake["Bronze / Raw (immutable)"]
        B1[(bronze/*.csv + streamed events)]
    end

    subgraph Processing
        P1[Schema validation]
        P2[PySpark/Pandas cleansing -> Silver]
        P3[Incremental load]
    end

    subgraph Warehouse["DuckDB Warehouse"]
        W1[(fact_flight, fact_booking, fact_baggage, fact_cancellation)]
        W2[(dim_airport, dim_route, dim_aircraft, dim_customer, dim_date)]
    end

    subgraph Marts["dbt Analytical Marts"]
        M1[mart_kpi_daily]
        M2[mart_route_profitability]
        M3[mart_delay_risk_features]
    end

    subgraph Intelligence
        I1[Delay prediction model]
        I2[Cancellation anomaly detector]
        I3[Route demand forecast]
    end

    subgraph Automation["Decision Engine"]
        D1{Rule evaluation}
        D2[/Notification: Email/Slack/Teams/]
        D3[(alerts table + audit log)]
    end

    subgraph App["API + Frontend"]
        F1[FastAPI]
        F2[React/Next.js Command Center]
    end

    A1 --> K3 --> B1
    A2 --> K1 --> B1
    A3 --> K2 --> B1
    B1 --> P1 --> P2 --> P3 --> W1
    P3 --> W2
    W1 --> M1 & M2 & M3
    M3 --> I1 & I2 & I3
    I1 & I2 & I3 --> D1
    M1 --> D1
    D1 -->|breach/risk detected| D2
    D1 --> D3
    W1 & M1 & M2 & I1 & I2 & I3 & D3 --> F1
    F1 --> F2
```

## Orchestration (Airflow DAG shape)

```mermaid
flowchart TD
    S[ingest_raw] --> V[validate_schema]
    V --> C[cleanse_to_silver]
    C --> L[load_warehouse_incremental]
    L --> T[dbt_run_and_test]
    T --> ML[refresh_ml_models]
    ML --> R[evaluate_automation_rules]
    R --> N[send_notifications]
    T --> DQ[data_quality_checks]
    DQ -->|fail| ALERT[pipeline_failure_alert]
```
