import os
import pandas as pd

from datetime import datetime, timezone

from dotenv import load_dotenv

from notification_engine import (
    send_operational_alert,
    send_operational_slack_alert
)


# =========================================================
# TRAVELOPS 360
# AUTOMATED NOTIFICATION ENGINE
# =========================================================

print("\n========================================")
print("TRAVELOPS 360 NOTIFICATION ENGINE")
print("========================================")


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FILE CONFIGURATION
# =========================================================

INPUT_FILE = (
    "analytics/outputs/automation_gap_actions.parquet"
)

OUTPUT_FILE = (
    "analytics/outputs/notification_audit.parquet"
)


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

OPERATIONS_EMAIL = os.getenv(
    "OPERATIONS_ALERT_EMAIL"
)

FLEET_EMAIL = os.getenv(
    "FLEET_ALERT_EMAIL"
)


# =========================================================
# SLACK CONFIGURATION
# =========================================================

SLACK_WEBHOOK_URL = os.getenv(
    "SLACK_WEBHOOK_URL"
)


# =========================================================
# VALIDATE EMAIL CONFIGURATION
# =========================================================

if not OPERATIONS_EMAIL:
    raise RuntimeError(
        "OPERATIONS_ALERT_EMAIL is missing from .env"
    )

if not FLEET_EMAIL:
    raise RuntimeError(
        "FLEET_ALERT_EMAIL is missing from .env"
    )


# =========================================================
# VALIDATE SLACK CONFIGURATION
# =========================================================

if not SLACK_WEBHOOK_URL:
    raise RuntimeError(
        "SLACK_WEBHOOK_URL is missing from .env"
    )


# =========================================================
# CHECK INPUT FILE
# =========================================================

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"\nAutomation output file not found:\n"
        f"{INPUT_FILE}\n\n"
        f"Run this command first:\n"
        f"python analytics\\automation_rules.py"
    )


# =========================================================
# LOAD AUTOMATION RESULTS
# =========================================================

print("\nLoading automation results...")

df = pd.read_parquet(
    INPUT_FILE
)

print(
    f"Total automation records: "
    f"{len(df)}"
)


# =========================================================
# SHOW ALERT TYPE DISTRIBUTION
# =========================================================

print("\nAlert type distribution:")

if "alert_type" in df.columns:
    print(
        df["alert_type"]
        .value_counts()
        .to_string()
    )


# =========================================================
# SHOW RISK DISTRIBUTION
# =========================================================

print("\nRisk distribution:")

if "risk_level" in df.columns:
    print(
        df["risk_level"]
        .value_counts()
        .to_string()
    )


# =========================================================
# SELECT ALERTS REQUIRING NOTIFICATION
# =========================================================

alerts = df[
    df["risk_level"].isin(
        [
            "HIGH",
            "MEDIUM"
        ]
    )
].copy()


# Also make sure notification is required
if "notification_required" in alerts.columns:
    alerts = alerts[
        alerts["notification_required"]
        .astype(bool)
    ]


# Only OPEN alerts
if "status" in alerts.columns:
    alerts = alerts[
        alerts["status"]
        .astype(str)
        .str.upper()
        == "OPEN"
    ]


print(
    f"\nAlerts requiring notification: "
    f"{len(alerts)}"
)


# =========================================================
# DEMO MODE
# =========================================================

# We do NOT send hundreds of notifications.
# We send a maximum of 5 alerts for demonstration/testing.
#
# We try to select different alert types first.
# If only one alert type exists in the dataset,
# we use that alert type.
# =========================================================

demo_alerts_list = []

preferred_alert_types = [
    "DELAY_RISK",
    "BAGGAGE_SLA_BREACH",
    "DEMAND_SURGE",
    "CANCELLATION_CLUSTER"
]


# ---------------------------------------------------------
# First select one alert from each available alert type
# ---------------------------------------------------------

for alert_type in preferred_alert_types:

    matching = alerts[
        alerts["alert_type"]
        .astype(str)
        .str.upper()
        == alert_type
    ]

    if not matching.empty:
        demo_alerts_list.append(
            matching.iloc[0]
        )


# ---------------------------------------------------------
# Fill remaining slots until we have maximum 5 alerts
# ---------------------------------------------------------

if len(demo_alerts_list) < 5:

    already_selected = [
        row.name
        for row in demo_alerts_list
    ]

    remaining = alerts[
        ~alerts.index.isin(
            already_selected
        )
    ]

    remaining_needed = (
        5 - len(demo_alerts_list)
    )

    for _, row in remaining.head(
        remaining_needed
    ).iterrows():

        demo_alerts_list.append(
            row
        )


# Convert selected alerts back to DataFrame

if demo_alerts_list:

    demo_alerts = pd.DataFrame(
        demo_alerts_list
    )

else:

    demo_alerts = pd.DataFrame(
        columns=alerts.columns
    )


print(
    f"Demo notifications to send: "
    f"{len(demo_alerts)}"
)


# =========================================================
# SEND NOTIFICATIONS
# =========================================================

audit_records = []


for _, row in demo_alerts.iterrows():

    alert = row.to_dict()

    # -----------------------------------------------------
    # UNIFIED AUTOMATION COLUMN NAMES
    # -----------------------------------------------------

    entity_id = alert.get(
        "entity_id",
        "UNKNOWN"
    )

    alert_id = alert.get(
        "alert_id",
        f"ALERT-{entity_id}"
    )

    alert_type = alert.get(
        "alert_type",
        "UNKNOWN"
    )

    risk_level = alert.get(
        "risk_level",
        "UNKNOWN"
    )

    priority = alert.get(
        "priority",
        None
    )

    automation_action = alert.get(
        "automation_action",
        "UNKNOWN"
    )

    trigger_reason = alert.get(
        "trigger_reason",
        alert.get(
            "action_message",
            "Operational risk detected."
        )
    )

    owner = alert.get(
        "owner",
        "Operations Control"
    )

    # -----------------------------------------------------
    # DETERMINE NOTIFICATION OWNER / RECIPIENT
    # -----------------------------------------------------

    if automation_action == (
        "AIRCRAFT_TURNAROUND_ALERT"
    ):

        recipient = FLEET_EMAIL

        notification_owner = (
            "Fleet Operations"
        )

    elif alert_type == (
        "BAGGAGE_SLA_BREACH"
    ):

        recipient = OPERATIONS_EMAIL

        notification_owner = (
            "Baggage Operations"
        )

    elif alert_type == (
        "DEMAND_SURGE"
    ):

        recipient = OPERATIONS_EMAIL

        notification_owner = (
            "Network Planning"
        )

    elif alert_type == (
        "CANCELLATION_CLUSTER"
    ):

        recipient = OPERATIONS_EMAIL

        notification_owner = (
            "Operations Control"
        )

    else:

        recipient = OPERATIONS_EMAIL

        notification_owner = (
            "Operations Control"
        )

    # -----------------------------------------------------
    # SEND EMAIL
    # -----------------------------------------------------

    try:

        result = send_operational_alert(
            alert=alert,
            recipient=recipient
        )

        timestamp = result.get(
            "timestamp",
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        audit_records.append(
            {
                "timestamp": timestamp,
                "alert_id": alert_id,
                "entity_id": entity_id,
                "alert_type": alert_type,
                "risk_level": risk_level,
                "priority": priority,
                "automation_action": automation_action,
                "trigger_reason": trigger_reason,
                "owner": notification_owner,
                "notification_channel": "EMAIL",
                "recipient": recipient,
                "status": "SENT"
            }
        )

        print(
            f"✓ EMAIL SENT | "
            f"{alert_type} | "
            f"{entity_id} | "
            f"{risk_level} | "
            f"{automation_action}"
        )

    except Exception as e:

        audit_records.append(
            {
                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                "alert_id": alert_id,
                "entity_id": entity_id,
                "alert_type": alert_type,
                "risk_level": risk_level,
                "priority": priority,
                "automation_action": automation_action,
                "trigger_reason": trigger_reason,
                "owner": notification_owner,
                "notification_channel": "EMAIL",
                "recipient": recipient,
                "status": "FAILED",
                "error": str(e)
            }
        )

        print(
            f"✗ EMAIL FAILED | "
            f"{alert_type} | "
            f"{entity_id} | "
            f"{e}"
        )

    # -----------------------------------------------------
    # SEND SLACK
    # -----------------------------------------------------

    try:

        slack_result = send_operational_slack_alert(
            alert=alert
        )

        slack_timestamp = slack_result.get(
            "timestamp",
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        audit_records.append(
            {
                "timestamp": slack_timestamp,
                "alert_id": alert_id,
                "entity_id": entity_id,
                "alert_type": alert_type,
                "risk_level": risk_level,
                "priority": priority,
                "automation_action": automation_action,
                "trigger_reason": trigger_reason,
                "owner": notification_owner,
                "notification_channel": "SLACK",
                "recipient": "Slack #all-travelops-360",
                "status": "SENT"
            }
        )

        print(
            f"✓ SLACK SENT | "
            f"{alert_type} | "
            f"{entity_id} | "
            f"{risk_level} | "
            f"{automation_action}"
        )

    except Exception as e:

        audit_records.append(
            {
                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                "alert_id": alert_id,
                "entity_id": entity_id,
                "alert_type": alert_type,
                "risk_level": risk_level,
                "priority": priority,
                "automation_action": automation_action,
                "trigger_reason": trigger_reason,
                "owner": notification_owner,
                "notification_channel": "SLACK",
                "recipient": "Slack #all-travelops-360",
                "status": "FAILED",
                "error": str(e)
            }
        )

        print(
            f"✗ SLACK FAILED | "
            f"{alert_type} | "
            f"{entity_id} | "
            f"{e}"
        )


# =========================================================
# CREATE AUDIT DATAFRAME
# =========================================================

audit_df = pd.DataFrame(
    audit_records
)


# =========================================================
# SAVE AUDIT LOG
# =========================================================

if not audit_df.empty:

    audit_df.to_parquet(
        OUTPUT_FILE,
        index=False
    )


# =========================================================
# FINAL SUMMARY
# =========================================================

print("\n========================================")
print("NOTIFICATION RUN COMPLETE")
print("========================================")

print(
    f"Alerts selected: "
    f"{len(demo_alerts)}"
)

if not audit_df.empty:

    sent_count = (
        audit_df["status"]
        == "SENT"
    ).sum()

    failed_count = (
        audit_df["status"]
        == "FAILED"
    ).sum()

    email_sent = (
        (audit_df["notification_channel"] == "EMAIL")
        & (audit_df["status"] == "SENT")
    ).sum()

    slack_sent = (
        (audit_df["notification_channel"] == "SLACK")
        & (audit_df["status"] == "SENT")
    ).sum()

else:

    sent_count = 0
    failed_count = 0
    email_sent = 0
    slack_sent = 0


print(
    f"Successfully sent: "
    f"{sent_count}"
)

print(
    f"Failed: "
    f"{failed_count}"
)

print(
    f"Email notifications sent: "
    f"{email_sent}"
)

print(
    f"Slack notifications sent: "
    f"{slack_sent}"
)

print(
    f"Audit file: "
    f"{OUTPUT_FILE}"
)

print("========================================")
