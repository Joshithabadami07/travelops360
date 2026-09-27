{{ config(materialized='table') }}

select
    flight_date,
    aircraft_id,
    count(*) as total_flights,
    sum(case when delay_minutes > 0 then 1 else 0 end) as delayed_flights,
    sum(case when is_cascade_delay = 1 then 1 else 0 end) as cascade_delay_flights,
    round(avg(delay_minutes), 2) as average_delay_minutes,
    round(avg(turnaround_minutes), 2) as average_turnaround_minutes,
    round(sum(propagated_delay_min), 2) as total_propagated_delay_minutes
from {{ ref('stg_rotation_delay') }}
group by
    flight_date,
    aircraft_id
