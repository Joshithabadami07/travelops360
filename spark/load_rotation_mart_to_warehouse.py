"""
Loads the PySpark rotation/delay-propagation output (partitioned parquet) into
the DuckDB warehouse. DuckDB reads parquet directly (via its parquet + hive
partitioning readers), so this step needs no Spark runtime — just duckdb.

Run after spark/rotation_delay_propagation.py has produced data/spark_output/:
  python3 spark/load_rotation_mart_to_warehouse.py
"""
import os
import duckdb

ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(ROOT, "data", "warehouse", "travelops.duckdb")
PARQUET_GLOB = os.path.join(ROOT, "data", "spark_output", "rotation_delay_propagation", "**", "*.parquet")

con = duckdb.connect(DB_PATH)
con.execute("SET SCHEMA 'travelops'")
con.execute(f"""
    CREATE OR REPLACE TABLE mart_rotation_delay_propagation AS
    SELECT * FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=1)
""")
n = con.sql("SELECT count(*) FROM mart_rotation_delay_propagation").fetchone()[0]
print(f"mart_rotation_delay_propagation loaded: {n:,} rows")
con.close()
