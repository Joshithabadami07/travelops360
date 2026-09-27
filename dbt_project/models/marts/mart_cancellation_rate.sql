-- KPI: Cancellation rate by route/day, plus reason mix for root-cause analysis.
with flights_per_day as (
    select route_id, scheduled_date_id as flight_date, count(*) as scheduled_flights
    from {{ ref('stg_flights') }}
    group by 1, 2
),
cancels_per_day as (
    select f.route_id, f.scheduled_date_id as flight_date,
           count(*) as cancelled_flights,
           mode(c.reason_code) as top_reason_code
    from {{ ref('stg_cancellations') }} c
    join {{ ref('stg_flights') }} f using (flight_id)
    group by 1, 2
)
select
    fpd.route_id, fpd.flight_date, fpd.scheduled_flights,
    coalesce(cpd.cancelled_flights, 0) as cancelled_flights,
    round(100.0 * coalesce(cpd.cancelled_flights, 0) / nullif(fpd.scheduled_flights, 0), 2) as cancellation_rate_pct,
    cpd.top_reason_code
from flights_per_day fpd
left join cancels_per_day cpd using (route_id, flight_date)
