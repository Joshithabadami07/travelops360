select route_id, origin_airport_id, dest_airport_id, popularity
from {{ source('travelops', 'dim_route') }}
