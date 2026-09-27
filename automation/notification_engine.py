import os
import smtplib
import requests

from datetime import datetime, timezone
from email.message import EmailMessage

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# EMAIL SENDER
# ============================================================

def send_email(subject: str, body: str, recipient: str):
    """Send an email using SMTP credentials from .env."""

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL")

    if not smtp_host:
        raise RuntimeError("SMTP_HOST is missing.")
    if not smtp_username:
        raise RuntimeError("SMTP_USERNAME is missing.")
    if not smtp_password:
        raise RuntimeError("SMTP_PASSWORD is missing.")
    if not sender_email:
        raise RuntimeError("SENDER_EMAIL is missing.")
    if not recipient:
        raise RuntimeError("Recipient email is missing.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


# ============================================================
# SLACK SENDER
# ============================================================

def send_slack(message: str):
    """Send a message to Slack through the Incoming Webhook."""

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL is missing from .env"
        )

    response = requests.post(
        webhook_url,
        json={"text": message},
        timeout=10
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Slack notification failed: "
            f"HTTP {response.status_code} - {response.text}"
        )

    if response.text.strip().lower() != "ok":
        raise RuntimeError(
            f"Slack returned an unexpected response: "
            f"{response.text}"
        )

    return True


# ============================================================
# ALERT FIELD HELPERS
# ============================================================

def get_flight_id(alert):
    """
    automation_gap_actions.parquet uses entity_id for the
    flight identifier.
    """

    return alert.get(
        "entity_id",
        alert.get("flight_id", "Unknown")
    )


def get_delay_probability(alert):
    """
    automation_gap_actions.parquet uses model_probability.
    """

    probability = alert.get(
        "model_probability",
        alert.get("delay_probability", 0)
    )

    try:
        probability = float(probability)
    except (TypeError, ValueError):
        probability = 0.0

    # Model probability is stored as a decimal, e.g. 0.9933.
    if probability <= 1:
        probability *= 100

    return probability


# ============================================================
# BUILD OPERATIONAL ALERT
# ============================================================

def build_alert_message(alert):
    """
    Build the email using the actual fields produced by
    automation_gap_actions.parquet.
    """

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    flight_id = get_flight_id(alert)

    risk_level = alert.get(
        "risk_level",
        "UNKNOWN"
    )

    automation_action = alert.get(
        "automation_action",
        "UNKNOWN"
    )

    trigger_reason = alert.get(
        "trigger_reason",
        "Operational risk detected."
    )

    owner = alert.get(
        "owner",
        "Operations Control"
    )

    alert_id = alert.get(
        "alert_id",
        f"ALERT-{flight_id}"
    )

    alert_type = alert.get(
        "alert_type",
        "UNKNOWN"
    )

    priority = alert.get(
        "priority",
        "N/A"
    )

    delay_probability = get_delay_probability(
        alert
    )

    subject = (
        f"[TravelOps 360] "
        f"{risk_level} Alert - "
        f"{flight_id}"
    )

    body = f"""
TRAVELOPS 360
AIRLINE OPERATIONS ALERT
========================================

Alert ID:
{alert_id}

Alert Type:
{alert_type}

Timestamp:
{timestamp}

Flight:
{flight_id}

Risk Level:
{risk_level}

Priority:
{priority}

Delay Probability:
{delay_probability:.1f}%

Automated Action:
{automation_action}

Trigger Reason:
{trigger_reason}

Owner:
{owner}

Status:
OPEN

========================================

This alert was generated automatically
by the TravelOps 360 decision engine.

Please review the flight and take the
required operational action.

TravelOps 360
Airline Operations Control Center
"""

    return subject, body


# ============================================================
# BUILD SLACK ALERT
# ============================================================

def build_slack_message(alert):
    """
    Build Slack message using the actual automation fields.
    """

    flight_id = get_flight_id(alert)

    alert_id = alert.get(
        "alert_id",
        f"ALERT-{flight_id}"
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
        "N/A"
    )

    automation_action = alert.get(
        "automation_action",
        "UNKNOWN"
    )

    trigger_reason = alert.get(
        "trigger_reason",
        "Operational risk detected."
    )

    owner = alert.get(
        "owner",
        "Operations Control"
    )

    delay_probability = get_delay_probability(
        alert
    )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    return f"""🚨 *TravelOps 360 - Operational Alert*

*Alert ID:* {alert_id}
*Alert Type:* {alert_type}
*Flight:* {flight_id}
*Risk Level:* {risk_level}
*Priority:* {priority}
*Delay Probability:* {delay_probability:.1f}%

*Automated Action:* {automation_action}
*Trigger Reason:* {trigger_reason}
*Owner:* {owner}
*Status:* OPEN

*Generated:* {timestamp}

TravelOps 360 Airline Operations Control Center"""


# ============================================================
# SEND OPERATIONAL EMAIL ALERT
# ============================================================

def send_operational_alert(alert, recipient):
    """Build and send an operational email alert."""

    subject, body = build_alert_message(
        alert
    )

    send_email(
        subject=subject,
        body=body,
        recipient=recipient
    )

    return {
        "success": True,
        "channel": "EMAIL",
        "flight_id": get_flight_id(alert),
        "recipient": recipient,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# SEND OPERATIONAL SLACK ALERT
# ============================================================

def send_operational_slack_alert(alert):
    """Build and send an operational Slack alert."""

    message = build_slack_message(
        alert
    )

    send_slack(message)

    return {
        "success": True,
        "channel": "SLACK",
        "flight_id": get_flight_id(alert),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }
