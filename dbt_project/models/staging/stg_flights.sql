select
    flight_id, route_id, aircraft_id, scheduled_date_id,
    scheduled_departure, actual_departure, status, delay_minutes
from {{ source('travelops', 'fact_flight') }}
