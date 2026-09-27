from datetime import datetime, timedelta
from pathlib import Path
import json

from airflow import DAG
from airflow.operators.python import PythonOperator


# TravelOps 360 project is mounted inside the Airflow container.
PROJECT_ROOT = Path("/opt/airflow/project")


def validate_source_data():
    """Validate that the required TravelOps 360 analytical files exist."""

    required_files = [
        "data/silver/flights.parquet",
        "data/silver/bookings.parquet",
        "data/silver/baggage.parquet",
        "data/silver/support_tickets.parquet",
        "analytics/outputs/route_profitability.parquet",
        "analytics/outputs/baggage_sla.parquet",
        "analytics/outputs/passenger_experience.parquet",
    ]

    missing = []

    for file_name in required_files:
        file_path = PROJECT_ROOT / file_name

        if not file_path.exists():
            missing.append(file_name)

    if missing:
        raise FileNotFoundError(
            "Missing required TravelOps 360 files:\n"
            + "\n".join(missing)
        )

    print("Source validation PASSED.")
    print(f"Validated {len(required_files)} required files.")


def run_data_quality():
    """Perform lightweight data-quality checks on the analytical files."""

    import pandas as pd

    checks = {
        "flights": "data/silver/flights.parquet",
        "bookings": "data/silver/bookings.parquet",
        "baggage": "data/silver/baggage.parquet",
        "support_tickets": "data/silver/support_tickets.parquet",
    }

    results = {}

    for name, relative_path in checks.items():
        path = PROJECT_ROOT / relative_path

        df = pd.read_parquet(path)

        null_rows = int(df.isnull().any(axis=1).sum())
        duplicate_rows = int(df.duplicated().sum())

        results[name] = {
            "rows": len(df),
            "columns": len(df.columns),
            "null_rows": null_rows,
            "duplicate_rows": duplicate_rows,
        }

        print(
            f"{name}: "
            f"rows={len(df)}, "
            f"null_rows={null_rows}, "
            f"duplicate_rows={duplicate_rows}"
        )

    print("Data-quality validation completed.")

    output_dir = PROJECT_ROOT / "analytics" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "airflow_data_quality.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def refresh_analytics():
    """Refresh the TravelOps 360 analytical outputs."""

    import subprocess

    script = PROJECT_ROOT / "analytics" / "build_gap_analytics.py"

    if not script.exists():
        raise FileNotFoundError(
            f"Analytics script not found: {script}"
        )

    result = subprocess.run(
        ["python", str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(
            "Analytics refresh failed."
        )

    print("Analytics refresh completed successfully.")


def refresh_automation():
    """Refresh automation decision outputs without sending notifications."""

    import subprocess

    script = PROJECT_ROOT / "analytics" / "automation_rules.py"

    if not script.exists():
        raise FileNotFoundError(
            f"Automation script not found: {script}"
        )

    result = subprocess.run(
        ["python", str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(
            "Automation refresh failed."
        )

    print("Automation rules refreshed successfully.")
    print("No email or Slack notifications were sent by this DAG.")


def validate_ml_outputs():
    """Verify that the trained ML artifacts are available."""

    required_outputs = [
        "analytics/outputs/flight_delay_future_model.pkl",
        "analytics/outputs/future_flight_delay_predictions.parquet",
        "analytics/outputs/demand_forecast.parquet",
        "analytics/outputs/cancellation_anomalies.parquet",
    ]

    missing = []

    for file_name in required_outputs:
        file_path = PROJECT_ROOT / file_name

        if not file_path.exists():
            missing.append(file_name)

    if missing:
        raise FileNotFoundError(
            "Missing ML/analytics outputs:\n"
            + "\n".join(missing)
        )

    print("ML and forecasting outputs validated.")
    print(f"Validated {len(required_outputs)} analytical artifacts.")


def create_pipeline_audit():
    """Create an audit record proving the Airflow pipeline completed."""

    output_dir = PROJECT_ROOT / "analytics" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    audit_file = output_dir / "airflow_pipeline_audit.json"

    audit_record = {
        "pipeline": "travelops360_batch_pipeline",
        "status": "SUCCESS",
        "completed_at_utc": datetime.utcnow().isoformat() + "Z",
        "stages": [
            "source_validation",
            "data_quality",
            "analytics_refresh",
            "automation_refresh",
            "ml_output_validation",
        ],
    }

    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(audit_record, f, indent=2)

    print("Airflow pipeline audit created:")
    print(audit_file)


default_args = {
    "owner": "TravelOps 360",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


with DAG(
    dag_id="travelops360_batch_pipeline",
    default_args=default_args,
    description="TravelOps 360 batch data, analytics, ML and automation pipeline",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["travelops360", "batch", "analytics", "ml", "automation"],
) as dag:

    source_validation = PythonOperator(
        task_id="validate_source_data",
        python_callable=validate_source_data,
    )

    data_quality = PythonOperator(
        task_id="run_data_quality",
        python_callable=run_data_quality,
    )

    analytics_refresh = PythonOperator(
        task_id="refresh_analytics",
        python_callable=refresh_analytics,
    )

    automation_refresh = PythonOperator(
        task_id="refresh_automation",
        python_callable=refresh_automation,
    )

    ml_validation = PythonOperator(
        task_id="validate_ml_outputs",
        python_callable=validate_ml_outputs,
    )

    pipeline_audit = PythonOperator(
        task_id="create_pipeline_audit",
        python_callable=create_pipeline_audit,
    )

    (
        source_validation
        >> data_quality
        >> analytics_refresh
        >> automation_refresh
        >> ml_validation
        >> pipeline_audit
    )