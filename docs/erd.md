# TravelOps 360 — ERD / Star Schema

## Warehouse star schema (target of Silver -> Gold / dbt marts)

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_FLIGHT : "departs on"
    DIM_AIRPORT ||--o{ FACT_FLIGHT : "origin"
    DIM_AIRPORT ||--o{ FACT_FLIGHT : "destination"
    DIM_ROUTE ||--o{ FACT_FLIGHT : "flown as"
    DIM_AIRCRAFT ||--o{ FACT_FLIGHT : "operated by"
    FACT_FLIGHT ||--o{ FACT_BOOKING : "carries"
    DIM_CUSTOMER ||--o{ FACT_BOOKING : "made by"
    FACT_BOOKING ||--o{ FACT_BAGGAGE : "checks"
    FACT_BOOKING ||--o{ FACT_SUPPORT_TICKET : "raises"
    FACT_FLIGHT ||--o| FACT_CANCELLATION : "may become"
    DIM_ROUTE ||--o{ FACT_FARE_SNAPSHOT : "priced as"

    DIM_DATE {
        string date_id PK
        int year
        int month
        string day_of_week
        bool is_weekend
    }
    DIM_AIRPORT {
        string airport_id PK
        string city
        string region
        int capacity
    }
    DIM_ROUTE {
        string route_id PK
        string origin_airport_id FK
        string dest_airport_id FK
        float popularity
    }
    DIM_AIRCRAFT {
        string aircraft_id PK
        string type
        int seat_capacity
    }
    DIM_CUSTOMER {
        string customer_id PK
        string tier
        string home_region
    }
    FACT_FLIGHT {
        string flight_id PK
        string route_id FK
        string aircraft_id FK
        string scheduled_date_id FK
        datetime scheduled_departure
        datetime actual_departure
        string status
        float delay_minutes
    }
    FACT_BOOKING {
        string booking_id PK
        string customer_id FK
        string flight_id FK
        float fare
        datetime booking_time
        string status
    }
    FACT_BAGGAGE {
        string bag_id PK
        string booking_id FK
        string airport FK
        datetime scan_time
        string status
    }
    FACT_CANCELLATION {
        string flight_id PK, FK
        datetime cancelled_at
        string reason_code
    }
    FACT_SUPPORT_TICKET {
        string ticket_id PK
        string booking_id FK
        string issue_type
        datetime created_at
    }
    FACT_FARE_SNAPSHOT {
        string route_id FK
        string cabin
        datetime timestamp
        float price
    }
```

## Source -> Target mapping (Bronze -> Silver -> Gold)

| Bronze source | Silver (cleansed) | Gold / Mart |
|---|---|---|
| flights.csv | silver_flights (deduped, typed, business-key validated) | fact_flight, fact_cancellation |
| bookings.csv | silver_bookings | fact_booking |
| baggage.csv | silver_baggage | fact_baggage |
| support_tickets.csv | silver_support | fact_support_ticket |
| fares.csv | silver_fares | fact_fare_snapshot |
| airports/aircraft/routes/customers/dim_date | silver_* (SCD-1 for now) | dim_airport, dim_aircraft, dim_route, dim_customer, dim_date |

Audit columns added at Silver: `_ingested_at`, `_source_file`, `_batch_id`, `_is_valid` (schema-validation flag).
