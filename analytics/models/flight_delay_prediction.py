import os
import glob
import pickle

import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


# ============================================================
# PATHS
# ============================================================

ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

SPARK_OUTPUT = os.path.join(
    ROOT,
    "data",
    "spark_output",
    "rotation_delay_propagation"
)

OUTPUT_DIR = os.path.join(
    ROOT,
    "analytics",
    "outputs"
)

MODEL_PATH = os.path.join(
    OUTPUT_DIR,
    "flight_delay_future_model.pkl"
)

PREDICTION_PATH = os.path.join(
    OUTPUT_DIR,
    "future_flight_delay_predictions.parquet"
)


# ============================================================
# START
# ============================================================

print("=" * 70)
print("TRAVELOPS 360 - FUTURE FLIGHT DELAY PREDICTION")
print("=" * 70)

print(f"\nProject root : {ROOT}")
print(f"Spark output : {SPARK_OUTPUT}")


# ============================================================
# FIND PARQUET FILES
# ============================================================

print("\nFinding Spark Parquet files...")

parquet_files = glob.glob(
    os.path.join(
        SPARK_OUTPUT,
        "**",
        "*.parquet"
    ),
    recursive=True
)

if not parquet_files:
    raise FileNotFoundError(
        f"\nNo Parquet files found in:\n{SPARK_OUTPUT}"
    )

print(
    f"Parquet files found: {len(parquet_files)}"
)


# ============================================================
# LOAD PARQUET DATA
# ============================================================

print("\nLoading rotation data...")

df = pd.concat(
    [
        pd.read_parquet(file)
        for file in parquet_files
    ],
    ignore_index=True
)

print(
    f"Rows loaded: {len(df)}"
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "flight_id",
    "aircraft_id",
    "route_id",
    "scheduled_departure",
    "actual_departure",
    "delay_minutes",
    "prev_flight_id",
    "prev_scheduled_departure",
    "prev_actual_departure",
    "prev_delay_minutes",
    "turnaround_minutes",
    "propagated_delay_min",
    "is_cascade_delay",
    "delay_propagation_flag"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        "\nMissing required columns:\n"
        + "\n".join(missing_columns)
    )


# ============================================================
# SORT DATA
# ============================================================

print("\nSorting flights...")

df["scheduled_departure"] = pd.to_datetime(
    df["scheduled_departure"],
    errors="coerce"
)

df["prev_actual_departure"] = pd.to_datetime(
    df["prev_actual_departure"],
    errors="coerce"
)

df = df.sort_values(
    [
        "aircraft_id",
        "scheduled_departure"
    ]
).reset_index(drop=True)


# ============================================================
# CREATE TARGET
# ============================================================

print("\nCreating future-delay target...")

df["future_delay"] = (
    df["delay_minutes"] > 0
).astype(int)


# ============================================================
# HISTORICAL FEATURES
# ============================================================

print("\nCreating historical features...")


# Previous flight delay

df["previous_flight_delay"] = (
    pd.to_numeric(
        df["prev_delay_minutes"],
        errors="coerce"
    )
    .fillna(0)
)


# Previous flight exists

df["previous_flight_exists"] = (
    df["prev_flight_id"]
    .notna()
).astype(int)


# Previous departure hour

df["previous_departure_hour"] = (
    df["prev_actual_departure"]
    .dt.hour
    .fillna(0)
)


# Current scheduled departure hour

df["scheduled_departure_hour"] = (
    df["scheduled_departure"]
    .dt.hour
    .fillna(0)
)


# Current scheduled departure day

df["scheduled_departure_day"] = (
    df["scheduled_departure"]
    .dt.dayofweek
    .fillna(0)
)


# Previous flight delayed flag

df["previous_flight_delayed"] = (
    df["previous_flight_delay"] > 0
).astype(int)


# Previous propagated delay

df["previous_propagated_delay"] = (
    pd.to_numeric(
        df["propagated_delay_min"],
        errors="coerce"
    )
    .fillna(0)
)


# Previous cascade indicator

df["previous_cascade_indicator"] = (
    pd.to_numeric(
        df["is_cascade_delay"],
        errors="coerce"
    )
    .fillna(0)
)


# ============================================================
# KEEP ONLY FLIGHTS WITH HISTORY
# ============================================================

model_df = df[
    df["previous_flight_exists"] == 1
].copy()

print(
    f"Rows with previous-flight history: {len(model_df)}"
)


# ============================================================
# FEATURES
# ============================================================

features = [
    "previous_flight_delay",
    "previous_flight_delayed",
    "previous_departure_hour",
    "scheduled_departure_hour",
    "scheduled_departure_day",
    "turnaround_minutes",
    "previous_propagated_delay",
    "previous_cascade_indicator"
]


# ============================================================
# PREPARE FEATURES
# ============================================================

X = model_df[features].copy()

X = X.apply(
    pd.to_numeric,
    errors="coerce"
)

X = X.fillna(0)

y = model_df["future_delay"]


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\nTarget distribution:")

print(
    y.value_counts()
    .sort_index()
)


if y.nunique() < 2:
    raise ValueError(
        "The target contains only one class."
    )


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

print("\nSplitting data...")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print(
    f"Training rows: {len(X_train)}"
)

print(
    f"Testing rows : {len(X_test)}"
)


# ============================================================
# TRAIN MODEL
# ============================================================

print("\nTraining Random Forest model...")

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    min_samples_split=5,
    random_state=42,
    class_weight="balanced"
)

model.fit(
    X_train,
    y_train
)

print("Training completed.")


# ============================================================
# EVALUATE
# ============================================================

print("\nEvaluating model...")

predictions = model.predict(
    X_test
)

accuracy = accuracy_score(
    y_test,
    predictions
)

print(
    "\nModel accuracy:",
    round(accuracy, 4)
)

print("\nClassification report:")

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\nFeature importance:")

importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_
}).sort_values(
    "importance",
    ascending=False
)

print(
    importance.to_string(
        index=False
    )
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE MODEL
# ============================================================

print("\nSaving model...")

with open(
    MODEL_PATH,
    "wb"
) as file:

    pickle.dump(
        model,
        file
    )

print(
    f"Model saved: {MODEL_PATH}"
)


# ============================================================
# GENERATE PREDICTIONS
# ============================================================

print("\nGenerating predictions...")

model_df["predicted_delay"] = (
    model.predict(X)
)

model_df["delay_probability"] = (
    model.predict_proba(X)[:, 1]
)


# ============================================================
# CREATE RISK LEVEL
# ============================================================

model_df["delay_risk_level"] = pd.cut(
    model_df["delay_probability"],
    bins=[
        -0.01,
        0.30,
        0.60,
        1.01
    ],
    labels=[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]
)


# ============================================================
# SAVE PREDICTIONS
# ============================================================

model_df.to_parquet(
    PREDICTION_PATH,
    index=False
)

print(
    f"Predictions saved: {PREDICTION_PATH}"
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("FUTURE DELAY MODEL COMPLETED")
print("=" * 70)

print(
    f"Rows used         : {len(model_df)}"
)

print(
    f"Test rows         : {len(X_test)}"
)

print(
    f"Model accuracy    : {round(accuracy, 4)}"
)

print(
    f"Model saved       : {MODEL_PATH}"
)

print(
    f"Predictions saved : {PREDICTION_PATH}"
)

print("=" * 70)