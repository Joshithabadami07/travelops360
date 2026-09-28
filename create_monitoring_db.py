import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WAREHOUSE = BASE_DIR / "data" / "warehouse" / "travelops.duckdb"
DEPLOYMENT = BASE_DIR / "deployment_data"
MONITORING_DB = DEPLOYMENT / "monitoring.duckdb"

MONITORING_PARQUET = DEPLOYMENT / "stream_monitoring.parquet"
EVENTS_PARQUET = DEPLOYMENT / "stream_seen_events.parquet"

DEPLOYMENT.mkdir(exist_ok=True)

# Read the original warehouse
source = duckdb.connect(str(WAREHOUSE), read_only=True)

source.execute(f"""
    COPY (
        SELECT *
        FROM travelops.travelops.stream_monitoring
    )
    TO '{MONITORING_PARQUET.as_posix()}'
    (FORMAT PARQUET)
""")

source.execute(f"""
    COPY (
        SELECT *
        FROM travelops.travelops.stream_seen_events
    )
    TO '{EVENTS_PARQUET.as_posix()}'
    (FORMAT PARQUET)
""")

source.close()

# Remove old deployment DB if it exists
if MONITORING_DB.exists():
    MONITORING_DB.unlink()

# Create deployment DB
destination = duckdb.connect(str(MONITORING_DB))

destination.execute(f"""
    CREATE TABLE stream_monitoring AS
    SELECT *
    FROM read_parquet('{MONITORING_PARQUET.as_posix()}')
""")

destination.execute(f"""
    CREATE TABLE stream_seen_events AS
    SELECT *
    FROM read_parquet('{EVENTS_PARQUET.as_posix()}')
""")

destination.close()

print("Monitoring database created successfully")
print(f"Database: {MONITORING_DB}")