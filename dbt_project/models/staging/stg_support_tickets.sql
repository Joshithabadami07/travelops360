select ticket_id, booking_id, issue_type, created_at
from {{ source('travelops', 'fact_support_ticket') }}
