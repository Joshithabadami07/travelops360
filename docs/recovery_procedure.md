# TravelOps 360 — Pipeline Failure Recovery Procedure

## Where failures surface
Every load step writes a row to `travelops.pipeline_run_log` (status `SUCCESS`/`FAILED`,
row counts, timestamps, and — on failure — the exception message). Every data-quality
check writes a row to `travelops.dq_check_log` (status `PASS`/`FAIL`, violation counts).
Start here:

```sql
SET SCHEMA 'travelops';
SELECT * FROM pipeline_run_log WHERE status = 'FAILED' ORDER BY started_at DESC;
SELECT * FROM dq_check_log WHERE status = 'FAIL' ORDER BY run_at DESC;
```

## Recovery steps, by failure type

### 1. Silver cleansing step fails / rejects spike unexpectedly
- Inspect `data/silver/_rejects/<table>_rejects.csv` — each row carries `_reject_reason`
  (`pk_null`, `duplicate_pk`, `<column>_null`, or a referential/business-rule failure
  applied upstream of `validate_and_split`).
- If the reject volume is a genuine source-system problem: fix or quarantine the source
  file, then re-run `python3 scripts/silver_transform.py` (it is safe to re-run — each
  run stamps a new `_batch_id` and fully re-derives Silver from the current Bronze files).
- If the reject rule itself is wrong (false positive): fix the rule in
  `scripts/silver_transform.py`, re-run, confirm reject count drops.

### 2. Warehouse load step fails (`load_warehouse.py`)
- Check the `error_message` column in `pipeline_run_log` for the failing task.
- The loader is **idempotent** (UPDATE-existing + INSERT-new-only, keyed on each table's
  primary key) — it is always safe to simply re-run
  `python3 scripts/load_warehouse.py` after fixing the underlying issue; it will not
  create duplicates.
- If the schema itself is out of date (a column was added/changed), run
  `python3 scripts/load_warehouse.py --rebuild` to drop and recreate the schema from
  `sql/schema.sql`, then reload. (Note: `--rebuild` is destructive to the warehouse —
  Bronze/Silver are untouched and remain the source of truth, so this is always
  recoverable.)

### 3. Data-quality check fails (`run_dq_checks.py` exits non-zero)
- The check name tells you the category (null / duplicate / referential-integrity /
  range / freshness / volume). Re-run the equivalent query in `sql/dq_checks.sql`
  directly against the warehouse to see the offending rows, not just the count.
- Referential-integrity failures at the warehouse layer (as opposed to Silver) indicate
  the Silver validation rules missed a case — treat this as a bug in
  `silver_transform.py`, not just a data problem, and add a regression case.
- In orchestration (see Week 3/4), a failing DQ run should **block** downstream
  ML/automation tasks from consuming that batch and should trigger a
  `pipeline_failure_alert` notification (see `docs/architecture.md` DAG diagram).

### 4. Freshness check fails (no new data landed)
- Confirm the upstream ingestion/streaming step actually produced a new batch
  (`_batch_id`/`_ingested_at` should advance each run).
- If ingestion is healthy but load didn't run, re-trigger the orchestrator task manually;
  no backfill logic is needed beyond re-running the (idempotent) load.

## General principles applied here
- **Idempotency everywhere**: every script in this pipeline can be safely re-run after a
  failure without manual cleanup — Bronze is immutable, Silver fully re-derives from
  Bronze, warehouse loads upsert on business key.
- **Fail loud, fail early**: `run_dq_checks.py` exits non-zero on any failed check so it
  can gate a real orchestrator (Airflow `ShortCircuitOperator` / task failure) rather than
  silently letting bad data flow downstream.
- **Audit trail over guesswork**: `pipeline_run_log` and `dq_check_log` are the first and
  only places you should need to look to diagnose "what broke and when."
