-- TravelOps 360 — Data Quality & Observability checks (run against the DuckDB warehouse)
-- Categories: null/dup/uniqueness, referential integrity, valid-range/business-rule,
-- freshness, volume. Each check is written to return 0 rows when it PASSES.

SET SCHEMA 'travelops';

-- ===================== 1. NULL / DUPLICATE / UNIQUENESS =====================

-- 1a. No nulls in any primary/business key
SELECT 'fact_flight.flight_id' AS check_name, count(*) AS violations FROM fact_flight WHERE flight_id IS NULL
UNION ALL
SELECT 'fact_booking.booking_id', count(*) FROM fact_booking WHERE booking_id IS NULL
UNION ALL
SELECT 'fact_baggage.bag_id', count(*) FROM fact_baggage WHERE bag_id IS NULL
UNION ALL
SELECT 'fact_support_ticket.ticket_id', count(*) FROM fact_support_ticket WHERE ticket_id IS NULL;

-- 1b. Uniqueness of primary keys (should return 0 rows if unique)
SELECT 'fact_flight' AS table_name, flight_id, count(*) AS n
FROM fact_flight GROUP BY flight_id HAVING count(*) > 1;

SELECT 'fact_booking' AS table_name, booking_id, count(*) AS n
FROM fact_booking GROUP BY booking_id HAVING count(*) > 1;

-- ===================== 2. REFERENTIAL INTEGRITY ==============================
-- (FKs are not hard-enforced at the DB layer — see sql/schema.sql note — so we
--  actively verify them here on every pipeline run.)

SELECT 'fact_booking->fact_flight' AS relationship, count(*) AS orphans
FROM fact_booking b LEFT JOIN fact_flight f ON b.flight_id = f.flight_id
WHERE f.flight_id IS NULL;

SELECT 'fact_booking->dim_customer' AS relationship, count(*) AS orphans
FROM fact_booking b LEFT JOIN dim_customer c ON b.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

SELECT 'fact_baggage->fact_booking' AS relationship, count(*) AS orphans
FROM fact_baggage bg LEFT JOIN fact_booking b ON bg.booking_id = b.booking_id
WHERE b.booking_id IS NULL;

SELECT 'fact_support_ticket->fact_booking' AS relationship, count(*) AS orphans
FROM fact_support_ticket s LEFT JOIN fact_booking b ON s.booking_id = b.booking_id
WHERE b.booking_id IS NULL;

SELECT 'fact_flight->dim_route' AS relationship, count(*) AS orphans
FROM fact_flight f LEFT JOIN dim_route r ON f.route_id = r.route_id
WHERE r.route_id IS NULL;

-- ===================== 3. VALID-RANGE / BUSINESS-RULE CHECKS =================

SELECT 'fact_flight.delay_minutes_negative' AS check_name, count(*) AS violations
FROM fact_flight WHERE delay_minutes < 0;

SELECT 'fact_booking.fare_non_positive' AS check_name, count(*) AS violations
FROM fact_booking WHERE fare <= 0;

SELECT 'fact_flight.status_invalid' AS check_name, count(*) AS violations
FROM fact_flight
WHERE status NOT IN ('SCHEDULED', 'BOARDING', 'DEPARTED', 'COMPLETED', 'CANCELLED');

SELECT 'fact_fare_snapshot.price_non_positive' AS check_name, count(*) AS violations
FROM fact_fare_snapshot WHERE price <= 0;

-- ===================== 4. FRESHNESS =========================================

SELECT 'fact_flight_freshness_hours' AS check_name,
       date_diff('hour', max(_ingested_at), now()) AS hours_since_last_load
FROM fact_flight;

-- ===================== 5. VOLUME (day-over-day sanity) =======================

WITH daily AS (
    SELECT scheduled_date_id, count(*) AS n_flights
    FROM fact_flight
    GROUP BY scheduled_date_id
)
SELECT scheduled_date_id, n_flights,
       avg(n_flights) OVER () AS avg_daily,
       CASE WHEN n_flights < 0.3 * avg(n_flights) OVER () THEN 'LOW_VOLUME_ALERT' ELSE 'OK' END AS flag
FROM daily
ORDER BY scheduled_date_id;
