select bag_id, booking_id, scan_time, airport, status
from {{ source('travelops', 'fact_baggage') }}
