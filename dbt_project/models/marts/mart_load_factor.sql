-- KPI: Load factor = booked seats / available seats, by route and day.
with flight_seats as (
    select f.flight_id, f.route_id, f.scheduled_date_id, ac.seat_capacity
    from {{ ref('stg_flights') }} f
    left join {{ ref('stg_aircraft') }} ac using (aircraft_id)
    where f.status in ('COMPLETED', 'DEPARTED', 'BOARDING')
),
booked as (
    select flight_id, count(*) as booked_seats
    from {{ ref('stg_bookings') }}
    where status not in ('REFUNDED')
    group by 1
)
select
    fs.route_id,
    fs.scheduled_date_id as flight_date,
    count(distinct fs.flight_id)              as flights,
    sum(coalesce(b.booked_seats, 0))           as booked_seats,
    sum(fs.seat_capacity)                       as available_seats,
    round(sum(coalesce(b.booked_seats, 0))::double
          / nullif(sum(fs.seat_capacity), 0), 4) as load_factor
from flight_seats fs
left join booked b using (flight_id)
group by 1, 2
