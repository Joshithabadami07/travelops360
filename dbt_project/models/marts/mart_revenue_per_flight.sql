-- KPI: Revenue per flight = route revenue attributed back to each completed flight.
select
    f.flight_id, f.route_id, f.scheduled_date_id as flight_date,
    count(b.booking_id)                as bookings,
    round(sum(b.fare), 2)              as flight_revenue,
    round(avg(b.fare), 2)              as avg_fare
from {{ ref('stg_flights') }} f
left join {{ ref('stg_bookings') }} b
    on b.flight_id = f.flight_id and b.status not in ('REFUNDED')
group by 1, 2, 3
