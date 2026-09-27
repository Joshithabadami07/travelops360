select flight_id, cancelled_at, reason_code
from {{ source('travelops', 'fact_cancellation') }}
