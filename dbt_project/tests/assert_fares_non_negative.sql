-- dbt test: fails (returns rows) if any booking fare is negative.
-- This is the dbt-native version of the valid-range/business-rule check
-- required in "Data Quality & Observability".
select booking_id, fare
from {{ ref('stg_bookings') }}
where fare < 0
