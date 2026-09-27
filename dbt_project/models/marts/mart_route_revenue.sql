-- KPI: Route revenue trend = confirmed-fare revenue by route/day.
select
    f.route_id,
    date_trunc('day', b.booking_time) as booking_date,
    count(*)              as bookings,
    round(sum(b.fare), 2) as route_revenue
from {{ ref('stg_bookings') }} b
join {{ ref('stg_flights') }} f using (flight_id)
where b.status not in ('REFUNDED')
group by 1, 2
