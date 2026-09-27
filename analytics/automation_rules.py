from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np


# ============================================================
# TRAVELOPS 360
# AUTOMATION RULE ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = BASE_DIR / "analytics" / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def read_file(filename):
    """
    Read a parquet file from analytics/outputs.
    """

    path = OUTPUT_DIR / filename

    if not path.exists():
        print(f"[WARN] File not found: {filename}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    print(f"[READ] {filename}")
    print(f"       rows={len(df):,}")

    return df


def find_column(df, possible_names):
    """
    Find the first matching column from a list.
    """

    for name in possible_names:
        if name in df.columns:
            return name

    return None


# ============================================================
# LOAD ANALYTICS OUTPUTS
# ============================================================

print("=" * 70)
print("TRAVELOPS 360 - AUTOMATION RULE ENGINE")
print("=" * 70)


delay_df = read_file(
    "delay_automation_actions.parquet"
)

baggage_df = read_file(
    "baggage_sla.parquet"
)

demand_df = read_file(
    "demand_forecast.parquet"
)

cancellation_df = read_file(
    "cancellation_anomalies.parquet"
)


all_alerts = []


# ============================================================
# 1. DELAY RISK AUTOMATION
# ============================================================

print()
print("[1/4] DELAY RISK AUTOMATION")


if not delay_df.empty:

    flight_col = find_column(
        delay_df,
        [
            "flight_id",
            "flight",
            "id"
        ]
    )

    risk_col = find_column(
        delay_df,
        [
            "risk_level",
            "risk",
            "severity"
        ]
    )

    action_col = find_column(
        delay_df,
        [
            "automation_action",
            "action"
        ]
    )

    probability_col = find_column(
        delay_df,
        [
            "future_delay_probability",
            "delay_probability",
            "probability",
            "prediction_probability"
        ]
    )

    reason_col = find_column(
        delay_df,
        [
            "trigger_reason",
            "reason"
        ]
    )

    for _, row in delay_df.iterrows():

        risk = (
            str(row[risk_col]).upper()
            if risk_col
            else ""
        )

        # Only HIGH and MEDIUM risks
        # require operational attention.
        if risk not in ["HIGH", "MEDIUM"]:
            continue

        flight_id = (
            str(row[flight_col])
            if flight_col
            else "UNKNOWN"
        )

        action = (
            str(row[action_col])
            if action_col
            else "OPERATIONS_REVIEW"
        )

        probability = 0.0

        if probability_col:
            try:
                probability = float(
                    row[probability_col]
                )
            except:
                probability = 0.0

        reason = (
            str(row[reason_col])
            if reason_col
            else
            "Predicted future flight delay risk."
        )

        all_alerts.append(
            {
                "alert_id":
                    f"DELAY-{flight_id}",

                "alert_type":
                    "DELAY_RISK",

                "entity_id":
                    flight_id,

                "risk_level":
                    risk,

                "priority":
                    1 if risk == "HIGH" else 2,

                "automation_action":
                    action,

                "trigger_reason":
                    reason,

                "model_probability":
                    probability,

                "owner":
                    "Operations Control",

                "status":
                    "OPEN",

                "notification_required":
                    True
            }
        )

    print(
        "       Delay alerts generated:",
        sum(
            a["alert_type"] == "DELAY_RISK"
            for a in all_alerts
        )
    )

else:

    print(
        "       No delay automation data found."
    )


# ============================================================
# 2. BAGGAGE SLA AUTOMATION
# ============================================================

print()
print("[2/4] BAGGAGE SLA AUTOMATION")


baggage_alerts = 0


if not baggage_df.empty:

    flight_col = find_column(
        baggage_df,
        [
            "flight_id",
            "flight",
            "id"
        ]
    )

    baggage_col = find_column(
        baggage_df,
        [
            "baggage_id",
            "bag_id",
            "bag_tag"
        ]
    )

    duration_col = find_column(
        baggage_df,
        [
            "cycle_minutes",
            "sla_minutes",
            "scan_duration_minutes",
            "duration_minutes",
            "processing_minutes"
        ]
    )

    breach_col = find_column(
        baggage_df,
        [
            "sla_breach",
            "breach",
            "is_breach"
        ]
    )


    # --------------------------------------------------------
    # Determine SLA breaches
    # --------------------------------------------------------

    if duration_col:

        duration_values = pd.to_numeric(
            baggage_df[duration_col],
            errors="coerce"
        )

        # 45-minute operational SLA
        breach_rows = baggage_df[
            duration_values > 45
        ].copy()

    elif breach_col:

        breach_values = (
            baggage_df[breach_col]
            .astype(str)
            .str.lower()
        )

        breach_rows = baggage_df[
            breach_values.isin(
                [
                    "true",
                    "1",
                    "yes",
                    "breach",
                    "high"
                ]
            )
        ].copy()

    else:

        breach_rows = pd.DataFrame()


    # Prevent thousands of emails during the demo.
    # We only create the first 100 automated alerts.
    breach_rows = breach_rows.head(100)


    for _, row in breach_rows.iterrows():

        flight_id = (
            str(row[flight_col])
            if flight_col
            else "UNKNOWN"
        )

        baggage_id = (
            str(row[baggage_col])
            if baggage_col
            else "UNKNOWN"
        )

        duration = 0.0

        if duration_col:
            try:
                duration = float(
                    row[duration_col]
                )
            except:
                duration = 0.0


        all_alerts.append(
            {
                "alert_id":
                    f"BAG-{baggage_id}",

                "alert_type":
                    "BAGGAGE_SLA_BREACH",

                "entity_id":
                    flight_id,

                "risk_level":
                    "HIGH",

                "priority":
                    1,

                "automation_action":
                    "BAGGAGE_SLA_ESCALATION",

                "trigger_reason":
                    (
                        "Baggage operational scan SLA "
                        f"exceeded 45 minutes "
                        f"({duration:.1f} minutes)."
                    ),

                "model_probability":
                    np.nan,

                "owner":
                    "Baggage Operations",

                "status":
                    "OPEN",

                "notification_required":
                    True
            }
        )

        baggage_alerts += 1


print(
    "       Baggage alerts generated:",
    baggage_alerts
)


# ============================================================
# 3. DEMAND SURGE AUTOMATION
# ============================================================

print()
print("[3/4] DEMAND SURGE AUTOMATION")


demand_alerts = 0


if not demand_df.empty:

    route_col = find_column(
        demand_df,
        [
            "route_id",
            "route",
            "route_code"
        ]
    )

    forecast_col = find_column(
        demand_df,
        [
            "predicted_demand",
            "forecast_demand",
            "forecast",
            "prediction"
        ]
    )

    actual_col = find_column(
        demand_df,
        [
            "actual_demand",
            "demand",
            "bookings",
            "booking_count"
        ]
    )


    if forecast_col:

        forecast_values = pd.to_numeric(
            demand_df[forecast_col],
            errors="coerce"
        ).fillna(0)


        # ----------------------------------------------------
        # If actual demand exists:
        # forecast >= 120% of actual = surge
        # ----------------------------------------------------

        if actual_col:

            actual_values = pd.to_numeric(
                demand_df[actual_col],
                errors="coerce"
            ).fillna(0)

            surge_mask = (
                forecast_values
                >= actual_values * 1.20
            )

            surge_rows = demand_df[
                surge_mask
            ].copy()


        # ----------------------------------------------------
        # Otherwise use top 25% forecasts
        # ----------------------------------------------------

        else:

            threshold = forecast_values.quantile(
                0.75
            )

            surge_rows = demand_df[
                forecast_values >= threshold
            ].copy()


    else:

        surge_rows = pd.DataFrame()


    # Limit alerts
    surge_rows = surge_rows.head(100)


    for _, row in surge_rows.iterrows():

        route_id = (
            str(row[route_col])
            if route_col
            else "UNKNOWN"
        )

        forecast = 0.0

        if forecast_col:
            try:
                forecast = float(
                    row[forecast_col]
                )
            except:
                forecast = 0.0


        all_alerts.append(
            {
                "alert_id":
                    f"DEMAND-{route_id}",

                "alert_type":
                    "DEMAND_SURGE",

                "entity_id":
                    route_id,

                "risk_level":
                    "MEDIUM",

                "priority":
                    2,

                "automation_action":
                    "DEMAND_SURGE_ALERT",

                "trigger_reason":
                    (
                        "Forecast demand surge detected "
                        f"for route {route_id}. "
                        f"Forecast demand={forecast:.0f}."
                    ),

                "model_probability":
                    np.nan,

                "owner":
                    "Network Planning",

                "status":
                    "OPEN",

                "notification_required":
                    True
            }
        )

        demand_alerts += 1


print(
    "       Demand alerts generated:",
    demand_alerts
)


# ============================================================
# 4. CANCELLATION CLUSTER AUTOMATION
# ============================================================

print()
print("[4/4] CANCELLATION CLUSTER AUTOMATION")


cancellation_alerts = 0


if not cancellation_df.empty:

    route_col = find_column(
        cancellation_df,
        [
            "route_id",
            "route",
            "route_code"
        ]
    )

    anomaly_col = find_column(
        cancellation_df,
        [
            "anomaly",
            "is_anomaly",
            "anomaly_flag"
        ]
    )

    zscore_col = find_column(
        cancellation_df,
        [
            "z_score",
            "zscore",
            "cancellation_zscore"
        ]
    )


    # --------------------------------------------------------
    # Detect anomaly rows
    # --------------------------------------------------------

    if anomaly_col:

        anomaly_values = (
            cancellation_df[anomaly_col]
            .astype(str)
            .str.lower()
        )

        anomaly_rows = cancellation_df[
            anomaly_values.isin(
                [
                    "true",
                    "1",
                    "yes",
                    "high",
                    "anomaly"
                ]
            )
        ].copy()


    elif zscore_col:

        z_values = pd.to_numeric(
            cancellation_df[zscore_col],
            errors="coerce"
        ).fillna(0)

        anomaly_rows = cancellation_df[
            z_values >= 2
        ].copy()


    else:

        anomaly_rows = pd.DataFrame()


    # Limit automated alerts
    anomaly_rows = anomaly_rows.head(100)


    for _, row in anomaly_rows.iterrows():

        route_id = (
            str(row[route_col])
            if route_col
            else "UNKNOWN"
        )

        zscore = 0.0

        if zscore_col:

            try:
                zscore = float(
                    row[zscore_col]
                )
            except:
                zscore = 0.0


        all_alerts.append(
            {
                "alert_id":
                    f"CANCEL-{route_id}",

                "alert_type":
                    "CANCELLATION_CLUSTER",

                "entity_id":
                    route_id,

                "risk_level":
                    "HIGH",

                "priority":
                    1,

                "automation_action":
                    "CANCELLATION_CLUSTER_ALERT",

                "trigger_reason":
                    (
                        "Cancellation anomaly detected "
                        f"for route {route_id}. "
                        f"Anomaly score={zscore:.2f}."
                    ),

                "model_probability":
                    np.nan,

                "owner":
                    "Operations Control",

                "status":
                    "OPEN",

                "notification_required":
                    True
            }
        )

        cancellation_alerts += 1


print(
    "       Cancellation alerts generated:",
    cancellation_alerts
)


# ============================================================
# CREATE FINAL AUTOMATION DATASET
# ============================================================

print()
print("=" * 70)
print("CREATING UNIFIED AUTOMATION TABLE")
print("=" * 70)


automation_df = pd.DataFrame(
    all_alerts
)


if automation_df.empty:

    print()
    print("[WARNING] No automation alerts generated.")

else:

    # Add timestamp
    automation_df.insert(
        0,
        "timestamp",
        datetime.now(
            timezone.utc
        ).isoformat()
    )


    # Audit event
    automation_df["audit_event"] = (
        "AUTOMATION_RULE_TRIGGERED"
    )


    # Save
    output_file = (
        OUTPUT_DIR /
        "automation_gap_actions.parquet"
    )


    automation_df.to_parquet(
        output_file,
        index=False
    )


    print()
    print(
        "[SAVE]",
        output_file
    )

    print(
        "       Total alerts:",
        f"{len(automation_df):,}"
    )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("Alert Types:")
    print(
        automation_df[
            "alert_type"
        ].value_counts().to_string()
    )


    print()
    print("Automation Actions:")
    print(
        automation_df[
            "automation_action"
        ].value_counts().to_string()
    )


    print()
    print("Risk Levels:")
    print(
        automation_df[
            "risk_level"
        ].value_counts().to_string()
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("AUTOMATION RULES COMPLETE")
print("=" * 70)