{{ config(materialized='view') }}

select
    flight_id,
    route_id,
    aircraft_id,
    scheduled_departure,
    actual_departure,
    status,
    delay_minutes,
    flight_date,
    rotation_sequence,
    prev_flight_id,
    prev_scheduled_departure,
    prev_actual_departure,
    prev_delay_minutes,
    turnaround_minutes,
    propagated_delay_min,
    is_cascade_delay,
    delay_propagation_flag
from read_parquet(
    '../data/spark_output/rotation_delay_propagation/**/*.parquet',
    hive_partitioning=true
)
