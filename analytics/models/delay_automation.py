import os
import pandas as pd


ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

PREDICTION_PATH = os.path.join(
    ROOT,
    "analytics",
    "outputs",
    "future_flight_delay_predictions.parquet"
)

OUTPUT_DIR = os.path.join(
    ROOT,
    "analytics",
    "outputs"
)

ACTION_PATH = os.path.join(
    OUTPUT_DIR,
    "delay_automation_actions.parquet"
)


print("=" * 70)
print("TRAVELOPS 360 - DELAY AUTOMATION ENGINE")
print("=" * 70)

print(f"\nPrediction file: {PREDICTION_PATH}")


if not os.path.exists(PREDICTION_PATH):
    raise FileNotFoundError(
        f"Prediction file not found:\n{PREDICTION_PATH}"
    )


print("\nLoading ML predictions...")

df = pd.read_parquet(
    PREDICTION_PATH
)

print(f"Rows loaded: {len(df)}")


def create_action(row):

    probability = row["delay_probability"]
    previous_delay = row["previous_flight_delay"]
    turnaround = row["turnaround_minutes"]
    cascade = row["previous_cascade_indicator"]

    if probability >= 0.70:

        if cascade == 1:
            return pd.Series([
                "HIGH",
                "URGENT_OPERATIONS_REVIEW",
                "Previous flight had cascade delay. Review aircraft rotation immediately."
            ])

        elif turnaround < 60:
            return pd.Series([
                "HIGH",
                "AIRCRAFT_TURNAROUND_ALERT",
                "High delay probability with short aircraft turnaround. Prioritize ground operations."
            ])

        else:
            return pd.Series([
                "HIGH",
                "OPERATIONS_REVIEW",
                "High predicted delay probability. Operations team review recommended."
            ])

    elif probability >= 0.40:

        if previous_delay > 30:
            return pd.Series([
                "MEDIUM",
                "MONITOR_AIRCRAFT",
                "Previous flight experienced significant delay. Monitor aircraft turnaround."
            ])

        else:
            return pd.Series([
                "MEDIUM",
                "MONITOR_FLIGHT",
                "Moderate predicted delay probability. Continue operational monitoring."
            ])

    else:

        return pd.Series([
            "LOW",
            "NO_ACTION",
            "Low predicted delay probability. No immediate action required."
        ])


print("\nGenerating automated actions...")

df[
    [
        "risk_level",
        "automation_action",
        "action_message"
    ]
] = df.apply(
    create_action,
    axis=1
)


df["priority"] = df["risk_level"].map({
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3
})


df = df.sort_values(
    [
        "priority",
        "delay_probability"
    ],
    ascending=[
        True,
        False
    ]
)


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


df.to_parquet(
    ACTION_PATH,
    index=False
)


print("\nAutomation summary:")

print(
    df["risk_level"].value_counts()
)


print("\nActions generated:")

print(
    df["automation_action"].value_counts()
)


print("\nTop 10 operational alerts:")

display_columns = [
    "flight_id",
    "aircraft_id",
    "route_id",
    "delay_probability",
    "risk_level",
    "automation_action",
    "action_message"
]

print(
    df[
        display_columns
    ]
    .head(10)
    .to_string(index=False)
)


print("\n" + "=" * 70)
print("AUTOMATION ENGINE COMPLETED")
print("=" * 70)

print(f"Input rows  : {len(df)}")
print(f"Output file : {ACTION_PATH}")

print("=" * 70)
