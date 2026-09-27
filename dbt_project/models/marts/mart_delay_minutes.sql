-- KPI: Delay minutes trend, overall and by route/day. Drives "delay risk" alerting.
select
    route_id,
    scheduled_date_id as flight_date,
    count(*)                                        as flights,
    sum(case when delay_minutes > 15 then 1 else 0 end) as delayed_flights,
    round(avg(delay_minutes), 2)                     as avg_delay_minutes,
    round(sum(delay_minutes), 2)                      as total_delay_minutes,
    round(100.0 * sum(case when delay_minutes > 15 then 1 else 0 end)
          / nullif(count(*), 0), 2)                   as pct_flights_delayed
from {{ ref('stg_flights') }}
where status in ('COMPLETED', 'DEPARTED')
group by 1, 2
