# TravelOps 360 — System Architecture

## 1. Overview

TravelOps 360 is an airline operations analytics platform that combines batch data processing, real-time event streaming, data-quality validation, analytical warehousing, machine learning, automated operational decisions, notifications, REST APIs, and a React-based command center.

The implemented architecture follows:

**Source Data → Ingestion → Bronze → Silver → Kafka / Stream Processing → DuckDB Warehouse → dbt → Analytics / ML → Automation → Notifications → FastAPI → React**

The project uses synthetic data for development and demonstration.

---

## 2. High-Level Architecture

```mermaid
flowchart TD

    A[Source Data]

    A1[Bookings]
    A2[Flights]
    A3[Baggage]
    A4[Airports]
    A5[Fares]
    A6[Support Tickets]

    A --> A1
    A --> A2
    A --> A3
    A --> A4
    A --> A5
    A --> A6

    A1 & A2 & A3 & A4 & A5 & A6 --> B[Data Ingestion]

    B --> C[Bronze / Raw Layer]

    C --> D[Silver Layer]
    D --> D1[Cleaning]
    D --> D2[Schema Validation]
    D --> D3[Data Quality]
    D --> D4[Metadata / Batch Tracking]

    D --> E[Analytical Warehouse]
    E --> E1[DuckDB]
    E --> E2[Fact Tables]
    E --> E3[Dimension Tables]

    E --> F[dbt]
    F --> F1[Staging Models]
    F --> F2[Analytical Marts]
    F --> F3[dbt Tests]

    D --> G[Kafka Streaming]

    G --> G1[flights.status]
    G --> G2[baggage.scans]
    G --> G3[bookings.events]

    G1 & G2 & G3 --> H[Stream Consumer]

    H --> H1[Event Processing]
    H --> H2[Duplicate Detection]
    H --> H3[Error Monitoring]
    H --> H4[Stream Monitoring]

    H --> E

    F --> I[Analytics]

    E --> I

    I --> I1[Route Profitability]
    I --> I2[Baggage SLA]
    I --> I3[Passenger Experience]
    I --> I4[Route Demand]
    I --> I5[Cancellation Analysis]

    I --> J[Machine Learning]

    J --> J1[Future Delay Prediction]
    J --> J2[Demand Forecast]
    J --> J3[Cancellation Anomaly Analysis]

    J --> K[Automation Engine]
    I --> K

    K --> K1[Delay Risk]
    K --> K2[Baggage SLA]
    K --> K3[Demand Surge]
    K --> K4[Cancellation Cluster]

    K --> L[Notifications]

    L --> L1[Email]
    L --> L2[Slack]

    L --> M[Notification Audit]

    E & I & J & K & M --> N[FastAPI]

    N --> N1[JWT Authentication]
    N --> N2[Dashboard APIs]
    N --> N3[Flight Risk APIs]
    N --> N4[Analytics APIs]
    N --> N5[Alert APIs]
    N --> N6[System Health]

    N --> O[React Command Center]

    O --> O1[Dashboard]
    O --> O2[Flight Operations]
    O --> O3[Alert Center]
    O --> O4[Risk Analytics]
    O --> O5[System Health]

    P[Apache Airflow] --> B
    P --> D
    P --> I
    P --> K
    P --> Q[Pipeline Audit]

    R[Docker] --> N
    R --> O

    S[GitHub Actions] --> T[Automated Tests]
