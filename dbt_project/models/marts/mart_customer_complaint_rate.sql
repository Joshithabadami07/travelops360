-- KPI: Customer complaint rate = support tickets per 1,000 bookings, by day and issue type.
with bookings_per_day as (
    select date_trunc('day', booking_time) as day, count(*) as bookings
    from {{ ref('stg_bookings') }}
    group by 1
),
tickets_per_day as (
    select date_trunc('day', created_at) as day, issue_type, count(*) as tickets
    from {{ ref('stg_support_tickets') }}
    group by 1, 2
)
select
    t.day, t.issue_type, t.tickets, b.bookings,
    round(1000.0 * t.tickets / nullif(b.bookings, 0), 2) as complaints_per_1000_bookings
from tickets_per_day t
join bookings_per_day b using (day)
