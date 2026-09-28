# TravelOps 360 — ERD and Star Schema

## 1. Overview

TravelOps 360 uses a dimensional warehouse model containing dimension tables, fact tables, live streaming tables, and operational monitoring tables.

The core analytical warehouse follows a star-schema approach.

The main business entities are:

- Flights
- Bookings
- Baggage
- Cancellations
- Fares
- Support Tickets
- Airports
- Routes
- Aircraft
- Customers
- Dates

The relationships documented below are logical relationships based on the implemented table columns and the project's referential-integrity checks.

---

# 2. Core Star Schema

```text
                           ┌─────────────────────┐
                           │    dim_aircraft     │
                           │─────────────────────│
                           │ PK aircraft_id      │
                           │ type                │
                           │ seat_capacity       │
                           └──────────┬──────────┘
                                      │
                                      │ aircraft_id
                                      │
                                      ▼
┌───────────────────┐       ┌─────────────────────┐
│    dim_route      │       │    fact_flight      │
│───────────────────│       │─────────────────────│
│ PK route_id       │◄──────│ PK flight_id        │
│ origin_airport_id │       │ FK route_id         │
│ dest_airport_id   │       │ FK aircraft_id      │
│ popularity        │       │ FK scheduled_date_id│
└────────┬──────────┘       │ scheduled_departure │
         │                  │ actual_departure    │
         │                  │ status              │
         │                  │ delay_minutes       │
         │                  └───────┬─────────────┘
         │                          │
         │                          │ flight_id
         │                          ▼
         │                  ┌─────────────────────┐
         │                  │ fact_cancellation   │
         │                  │─────────────────────│
         │                  │ PK flight_id       │
         │                  │ cancelled_at       │
         │                  │ reason_code        │
         │                  └─────────────────────┘
         │
         │ route_id
         ▼
┌─────────────────────┐
│ fact_fare_snapshot  │
│─────────────────────│
│ PK route_id         │
│ PK cabin            │
│ PK timestamp        │
│ price               │
└─────────────────────┘


                 ┌─────────────────────┐
                 │      dim_date       │
                 │─────────────────────│
                 │ PK date_id          │
                 │ date                │
                 │ year                │
                 │ month               │
                 │ day                 │
                 │ day_of_week         │
                 │ is_weekend          │
                 └──────────┬──────────┘
                            │
                            │ date_id
                            ▼
                     fact_flight


                 ┌─────────────────────┐
                 │    dim_airport      │
                 │─────────────────────│
                 │ PK airport_id       │
                 │ city                │
                 │ region              │
                 │ capacity            │
                 └───────┬───────┬─────┘
                         │       │
              origin_airport_id  │ dest_airport_id
                         │       │
                         └───┬───┘
                             ▼
                         dim_route


┌─────────────────────┐
│    dim_customer     │
│─────────────────────│
│ PK customer_id      │
│ name                │
│ tier                │
│ home_region         │
└──────────┬──────────┘
           │
           │ customer_id
           ▼
┌─────────────────────┐
│    fact_booking     │
│─────────────────────│
│ PK booking_id       │
│ FK customer_id      │
│ FK flight_id        │
│ fare                │
│ booking_time        │
│ status              │
└──────────┬──────────┘
           │
           │ booking_id
      ┌────┴─────────────────┐
      │                      │
      ▼                      ▼
┌──────────────────┐  ┌─────────────────────┐
│  fact_baggage    │  │ fact_support_ticket │
│──────────────────│  │─────────────────────│
│ PK bag_id        │  │ PK ticket_id        │
│ FK booking_id    │  │ FK booking_id       │
│ scan_time        │  │ issue_type          │
│ airport          │  │ created_at          │
│ status           │  └─────────────────────┘
└──────────────────┘