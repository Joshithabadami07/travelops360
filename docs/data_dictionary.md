# TravelOps 360 — Data Dictionary

## 1. Purpose

This data dictionary documents the core warehouse tables used by TravelOps 360.

It defines:

- Table purpose
- Table grain
- Primary keys
- Logical foreign keys
- Business fields
- Data types
- Metadata fields
- Streaming and monitoring fields

The definitions are based on the implemented DuckDB warehouse schema.

---

# 2. Data Model Overview

The core analytical warehouse contains:

## Dimensions

- `dim_aircraft`
- `dim_airport`
- `dim_customer`
- `dim_date`
- `dim_route`

## Facts

- `fact_flight`
- `fact_booking`
- `fact_baggage`
- `fact_cancellation`
- `fact_fare_snapshot`
- `fact_support_ticket`

## Live Streaming Tables

- `fact_flight_status_live`
- `fact_baggage_scan_live`
- `fact_booking_live`

## Monitoring / Governance Tables

- `stream_seen_events`
- `stream_monitoring`
- `dq_check_log`
- `pipeline_run_log`

## Analytical Mart

- `mart_rotation_delay_propagation`

---

# 3. Common Metadata Fields

Most historical warehouse tables contain the following ingestion metadata.

| Field | Type | Description |
|---|---|---|
| `_source_file` | VARCHAR | Source file from which the record originated |
| `_batch_id` | VARCHAR | Identifier for the ingestion/transformation batch |
| `_ingested_at` | TIMESTAMP | Timestamp at which the record was ingested |

These fields support:

- Data lineage
- Source traceability
- Batch tracking
- Auditability
- Pipeline troubleshooting

---

# 4. Dimension Tables

## 4.1 dim_aircraft

### Purpose

Stores aircraft reference information.

### Grain

One row per aircraft.

### Primary Key

`aircraft_id`

| Field | Type | Key | Description |
|---|---|---|---|
| `aircraft_id` | VARCHAR | PK | Unique identifier for an aircraft |
| `type` | VARCHAR | | Aircraft type |
| `seat_capacity` | INTEGER | | Number of seats available on the aircraft |
| `_source_file` | VARCHAR | Metadata | Source file |
| `_batch_id` | VARCHAR | Metadata | Ingestion batch identifier |
| `_ingested_at` | TIMESTAMP | Metadata | Record ingestion timestamp |

---

## 4.2 dim_airport

### Purpose

Stores airport reference information.

### Grain

One row per airport.

### Primary Key

`airport_id`

| Field | Type | Key | Description |
|---|---|---|---|
| `airport_id` | VARCHAR | PK | Unique identifier for an airport |
| `city` | VARCHAR | | City associated with the airport |
| `region` | VARCHAR | | Geographic region |
| `capacity` | INTEGER | | Airport capacity measure |
| `_source_file` | VARCHAR | Metadata | Source file |
| `_batch_id` | VARCHAR | Metadata | Ingestion batch identifier |
| `_ingested_at` | TIMESTAMP | Metadata | Record ingestion timestamp |

---

## 4.3 dim_customer

### Purpose

Stores customer reference information used for passenger and booking analysis.

### Grain

One row per customer.

### Primary Key

`customer_id`

| Field | Type | Key | Description |
|---|---|---|---|
| `customer_id` | VARCHAR | PK | Unique customer identifier |
| `name` | VARCHAR | | Customer name |
| `tier` | VARCHAR | | Customer tier |
| `home_region` | VARCHAR | | Customer's home region |
| `_source_file` | VARCHAR | Metadata | Source file |
| `_batch_id` | VARCHAR | Metadata | Ingestion batch identifier |
| `_ingested_at` | TIMESTAMP | Metadata | Record ingestion timestamp |

---

## 4.4 dim_date

### Purpose

Provides calendar attributes for time-based analysis.

### Grain

One row per date.

### Primary Key

`date_id`

| Field | Type | Key | Description |
|---|---|---|---|
| `date_id` | VARCHAR | PK | Unique date-dimension identifier |
| `date` | DATE | | Calendar date |
| `year` | INTEGER | | Calendar year |
| `month` | INTEGER | | Calendar month |
| `day` | INTEGER | | Calendar day |
| `day_of_week` | VARCHAR | | Name/representation of the day of the week |
| `is_weekend` | BOOLEAN | | Indicates whether the date is a weekend |
| `_source_file` | VARCHAR | Metadata | Source file |
| `_batch_id` | VARCHAR | Metadata | Ingestion batch identifier |
| `_ingested_at` | TIMESTAMP | Metadata | Record ingestion timestamp |

---

## 4.5 dim_route

### Purpose

Stores route-level reference information.

### Grain

One row per route.

### Primary Key

`route_id`

| Field | Type | Key | Description |
|---|---|---|---|
| `route_id` | VARCHAR | PK | Unique route identifier |
| `origin_airport_id` | VARCHAR | Logical FK | Airport from which the route originates |
| `dest_airport_id` | VARCHAR | Logical FK | Destination airport |
| `popularity` | DOUBLE | | Route popularity measure |
| `_source_file` | VARCHAR | Metadata | Source file |
| `_batch_id` | VARCHAR | Metadata | Ingestion batch identifier |
| `_ingested_at` | TIMESTAMP | Metadata | Record ingestion timestamp |

### Relationships

```text
origin_airport_id → dim_airport.airport_id
dest_airport_id   → dim_airport.airport_id