select booking_id, customer_id, flight_id, fare, booking_time, status
from {{ source('travelops', 'fact_booking') }}
