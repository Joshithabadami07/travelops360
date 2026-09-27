-- KPI: Baggage SLA = share of bags NOT delayed, by airport/day.
select
    airport,
    date_trunc('day', scan_time) as scan_date,
    count(*)                                              as bags_scanned,
    sum(case when status = 'DELAYED' then 1 else 0 end)   as sla_breaches,
    round(100.0 * (1 - sum(case when status = 'DELAYED' then 1 else 0 end)::double
          / nullif(count(*), 0)), 2)                       as baggage_sla_pct
from {{ ref('stg_baggage') }}
group by 1, 2
