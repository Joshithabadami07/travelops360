select airport_id, city, region, capacity
from {{ source('travelops', 'dim_airport') }}
