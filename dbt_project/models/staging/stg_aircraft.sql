select aircraft_id, type, seat_capacity
from {{ source('travelops', 'dim_aircraft') }}
