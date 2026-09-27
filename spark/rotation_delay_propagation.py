import os
import shutil

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from pyspark.sql import SparkSession
from pyspark.sql import Window
from pyspark.sql import functions as F


# ============================================================
# PATHS
# ============================================================

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SILVER = os.path.join(
    ROOT,
    "data",
    "silver",
    "flights.parquet"
)

OUT = os.path.join(
    ROOT,
    "data",
    "spark_output"
)

OUTPUT_PATH = os.path.join(
    OUT,
    "rotation_delay_propagation"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TRAVELOPS 360 - ROTATION DELAY PROPAGATION")
    print("=" * 70)

    # --------------------------------------------------------
    # START SPARK
    # --------------------------------------------------------

    spark = (
        SparkSession.builder
        .appName("TravelOps360-RotationDelayPropagation")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:

        # ----------------------------------------------------
        # 1. READ SILVER DATA
        # ----------------------------------------------------

        print("\n[1/6] Reading Silver flight data...")

        flights = spark.read.parquet(SILVER)

        print(f"Silver file: {SILVER}")
        print(f"Columns: {flights.columns}")

        # ----------------------------------------------------
        # 2. SELECT ACTUAL AVAILABLE COLUMNS
        # ----------------------------------------------------

        print("\n[2/6] Preparing flight data...")

        flights = flights.select(
            "flight_id",
            "route_id",
            "aircraft_id",
            "scheduled_departure",
            "actual_departure",
            "status",
            "delay_minutes"
        )

        # ----------------------------------------------------
        # CREATE FLIGHT DATE
        # ----------------------------------------------------

        flights = flights.withColumn(
            "flight_date",
            F.to_date("scheduled_departure")
        )

        # ----------------------------------------------------
        # NORMALIZE DELAY
        # ----------------------------------------------------

        flights = flights.withColumn(
            "delay_minutes",
            F.coalesce(
                F.col("delay_minutes").cast("double"),
                F.lit(0.0)
            )
        )

        # ----------------------------------------------------
        # 3. AIRCRAFT ROTATION WINDOW
        # ----------------------------------------------------

        print("\n[3/6] Calculating aircraft rotation...")

        rotation_window = (
            Window
            .partitionBy(
                "aircraft_id",
                "flight_date"
            )
            .orderBy(
                F.col("scheduled_departure"),
                F.col("flight_id")
            )
        )

        # ----------------------------------------------------
        # PREVIOUS FLIGHT
        # ----------------------------------------------------

        result = (
            flights

            .withColumn(
                "rotation_sequence",
                F.row_number().over(rotation_window)
            )

            .withColumn(
                "prev_flight_id",
                F.lag("flight_id").over(rotation_window)
            )

            .withColumn(
                "prev_scheduled_departure",
                F.lag("scheduled_departure").over(rotation_window)
            )

            .withColumn(
                "prev_actual_departure",
                F.lag("actual_departure").over(rotation_window)
            )

            .withColumn(
                "prev_delay_minutes",
                F.lag("delay_minutes").over(rotation_window)
            )
        )

        # ----------------------------------------------------
        # TURNAROUND TIME
        # ----------------------------------------------------

        result = result.withColumn(
            "turnaround_minutes",
            F.when(
                F.col("prev_actual_departure").isNotNull(),
                (
                    F.unix_timestamp("scheduled_departure")
                    -
                    F.unix_timestamp("prev_actual_departure")
                ) / 60.0
            ).otherwise(None)
        )

        # ----------------------------------------------------
        # PROPAGATED DELAY
        # ----------------------------------------------------

        result = result.withColumn(
            "propagated_delay_min",
            F.when(
                F.col("prev_delay_minutes") > 0,
                F.col("prev_delay_minutes")
            ).otherwise(
                F.lit(0.0)
            )
        )

        # ----------------------------------------------------
        # CASCADE DELAY
        # ----------------------------------------------------

        result = result.withColumn(
            "is_cascade_delay",
            F.when(
                (
                    (F.col("prev_delay_minutes") > 0)
                    &
                    (F.col("delay_minutes") > 0)
                ),
                F.lit(1)
            ).otherwise(
                F.lit(0)
            )
        )

        # ----------------------------------------------------
        # DELAY PROPAGATION FLAG
        # ----------------------------------------------------

        result = result.withColumn(
            "delay_propagation_flag",
            F.when(
                F.col("is_cascade_delay") == 1,
                F.lit("PROPAGATED")
            )
            .when(
                F.col("delay_minutes") > 0,
                F.lit("PRIMARY_DELAY")
            )
            .otherwise(
                F.lit("NO_DELAY")
            )
        )

        # ----------------------------------------------------
        # 4. FINAL RESULT
        # ----------------------------------------------------

        print("\n[4/6] Creating final analytical dataset...")

        result = result.select(
            "flight_id",
            "route_id",
            "aircraft_id",
            "flight_date",
            "rotation_sequence",
            "scheduled_departure",
            "actual_departure",
            "status",
            "delay_minutes",
            "prev_flight_id",
            "prev_scheduled_departure",
            "prev_actual_departure",
            "prev_delay_minutes",
            "turnaround_minutes",
            "propagated_delay_min",
            "is_cascade_delay",
            "delay_propagation_flag"
        )

        # ----------------------------------------------------
        # COUNT RESULTS
        # ----------------------------------------------------

        total_rows = result.count()

        cascade_rows = (
            result
            .filter(
                F.col("is_cascade_delay") == 1
            )
            .count()
        )

        print(f"Total rows: {total_rows}")
        print(f"Cascade delay rows: {cascade_rows}")

        # ----------------------------------------------------
        # 5. CONVERT TO PANDAS
        # ----------------------------------------------------

        print("\n[5/6] Converting Spark result to Parquet...")

        pandas_result = result.toPandas()

        # ----------------------------------------------------
        # DELETE OLD OUTPUT
        # ----------------------------------------------------

        if os.path.exists(OUTPUT_PATH):
            shutil.rmtree(OUTPUT_PATH)

        os.makedirs(OUTPUT_PATH, exist_ok=True)

        # ----------------------------------------------------
        # WRITE PARQUET USING PYARROW
        # ----------------------------------------------------

        arrow_table = pa.Table.from_pandas(
            pandas_result,
            preserve_index=False
        )

        pq.write_to_dataset(
            arrow_table,
            root_path=OUTPUT_PATH,
            partition_cols=["flight_date"]
        )

        # ----------------------------------------------------
        # 6. VERIFY
        # ----------------------------------------------------

        print("\n[6/6] Verifying output...")

        parquet_files = []

        for root, dirs, files in os.walk(OUTPUT_PATH):

            for file in files:

                if file.endswith(".parquet"):

                    parquet_files.append(
                        os.path.join(root, file)
                    )

        print("\n" + "=" * 70)
        print("ROTATION DELAY PROPAGATION COMPLETED")
        print("=" * 70)

        print(f"Input rows       : {total_rows}")
        print(f"Cascade delays   : {cascade_rows}")
        print(f"Parquet files    : {len(parquet_files)}")
        print(f"Output directory : {OUTPUT_PATH}")

        print("=" * 70)

    finally:

        spark.stop()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()