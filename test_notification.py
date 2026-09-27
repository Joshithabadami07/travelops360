from automation.notification_engine import send_operational_alert


test_alert = {
    "flight_id": "FL_TEST001",
    "aircraft_id": "AC_TEST001",
    "route_id": "RT_TEST001",
    "delay_probability": 0.9934,
    "risk_level": "HIGH",
    "automation_action": "URGENT_OPERATIONS_REVIEW",
    "action_message": (
        "Previous flight had cascade delay. "
        "Review aircraft rotation immediately."
    )
}


recipient = "joshithabadami@gmail.com"


result = send_operational_alert(
    test_alert,
    recipient
)


print("\nNotification result:")
print(result)