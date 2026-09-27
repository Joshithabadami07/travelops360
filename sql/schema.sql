-- TravelOps 360 — Warehouse DDL (DuckDB)
-- Star schema: dims + facts, with primary/business keys and audit columns for lineage.
--
-- NOTE on referential integrity: PKs are enforced (PRIMARY KEY). Foreign keys are
-- declared logically in docs/erd.md but NOT enforced as hard DB constraints here —
-- this matches how BigQuery/Snowflake actually behave in production (FKs there are
-- informational/optimizer hints, not enforced) and avoids DuckDB's copy-on-write
-- UPDATE colliding with FK checks during incremental upserts. Referential integrity
-- is instead actively verified by the automated checks in sql/dq_checks.sql, which
-- is the correct place for it per the "Data Quality & Observability" requirement.

DROP SCHEMA IF EXISTS travelops CASCADE;
CREATE SCHEMA travelops;
SET SCHEMA 'travelops';

-- ============================= DIMENSIONS =================================

CREATE TABLE dim_airport (
    airport_id      VARCHAR PRIMARY KEY,
    city            VARCHAR,
    region          VARCHAR,
    capacity        INTEGER,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE dim_aircraft (
    aircraft_id     VARCHAR PRIMARY KEY,
    type            VARCHAR,
    seat_capacity   INTEGER,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE dim_route (
    route_id            VARCHAR PRIMARY KEY,
    origin_airport_id   VARCHAR,
    dest_airport_id     VARCHAR,
    popularity          DOUBLE,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE dim_customer (
    customer_id     VARCHAR PRIMARY KEY,
    name            VARCHAR,
    tier            VARCHAR,
    home_region     VARCHAR,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE dim_date (
    date_id         VARCHAR PRIMARY KEY,
    date            DATE,
    year            INTEGER,
    month           INTEGER,
    day             INTEGER,
    day_of_week     VARCHAR,
    is_weekend      BOOLEAN,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

-- ============================== FACTS ======================================

CREATE TABLE fact_flight (
    flight_id            VARCHAR PRIMARY KEY,
    route_id             VARCHAR,
    aircraft_id          VARCHAR,
    scheduled_date_id    VARCHAR,
    scheduled_departure  TIMESTAMP,
    actual_departure     TIMESTAMP,
    status               VARCHAR,
    delay_minutes        DOUBLE,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE fact_cancellation (
    flight_id       VARCHAR PRIMARY KEY,
    cancelled_at    TIMESTAMP,
    reason_code     VARCHAR,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE fact_booking (
    booking_id      VARCHAR PRIMARY KEY,
    customer_id     VARCHAR,
    flight_id       VARCHAR,
    fare            DOUBLE,
    booking_time    TIMESTAMP,
    status          VARCHAR,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE fact_baggage (
    bag_id          VARCHAR PRIMARY KEY,
    booking_id      VARCHAR,
    scan_time       TIMESTAMP,
    airport         VARCHAR,
    status          VARCHAR,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE fact_support_ticket (
    ticket_id       VARCHAR PRIMARY KEY,
    booking_id      VARCHAR,
    issue_type      VARCHAR,
    created_at      TIMESTAMP,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP
);

CREATE TABLE fact_fare_snapshot (
    route_id        VARCHAR,
    cabin           VARCHAR,
    timestamp       TIMESTAMP,
    price           DOUBLE,
    _source_file    VARCHAR,
    _batch_id       VARCHAR,
    _ingested_at    TIMESTAMP,
    PRIMARY KEY (route_id, cabin, timestamp)
);

-- ============================= AUDIT / DQ ==================================

CREATE TABLE dq_check_log (
    check_id        VARCHAR,
    check_name      VARCHAR,
    table_name      VARCHAR,
    status          VARCHAR,     -- PASS / FAIL
    details         VARCHAR,
    run_at          TIMESTAMP,
    batch_id        VARCHAR
);

CREATE TABLE pipeline_run_log (
    run_id          VARCHAR,
    task_name       VARCHAR,
    status          VARCHAR,     -- SUCCESS / FAILED
    rows_affected   INTEGER,
    started_at      TIMESTAMP,
    ended_at        TIMESTAMP,
    error_message   VARCHAR
);

-- Helpful indexes for common query patterns (clustering-equivalent in DuckDB)
CREATE INDEX idx_fact_flight_date ON fact_flight(scheduled_date_id);
CREATE INDEX idx_fact_flight_route ON fact_flight(route_id);
CREATE INDEX idx_fact_booking_flight ON fact_booking(flight_id);
CREATE INDEX idx_fact_baggage_booking ON fact_baggage(booking_id);
CREATE INDEX idx_fact_support_booking ON fact_support_ticket(booking_id);
