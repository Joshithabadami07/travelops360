from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_project_directories_exist():
    required_directories = [
        "api",
        "analytics",
        "automation",
        "airflow",
        "frontend",
        "spark",
        "sql",
        "streaming",
        "dbt_project",
        "docs",
    ]

    for directory in required_directories:
        path = PROJECT_ROOT / directory
        assert path.exists(), f"Missing required directory: {directory}"
        assert path.is_dir(), f"Expected directory but found something else: {directory}"


def test_required_project_files_exist():
    required_files = [
        "Dockerfile",
        "requirements.txt",
        "README.md",
        "api/main.py",
        "analytics/build_gap_analytics.py",
        "analytics/automation_rules.py",
        "automation/notification_engine.py",
        "streaming/producer.py",
        "streaming/consumer.py",
        "airflow/dags/travelops360_pipeline.py",
    ]

    for file_path in required_files:
        path = PROJECT_ROOT / file_path
        assert path.exists(), f"Missing required file: {file_path}"
        assert path.is_file(), f"Expected file but found something else: {file_path}"