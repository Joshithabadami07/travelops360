import os

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_protected_endpoint_requires_authentication():
    response = client.get("/summary")

    assert response.status_code == 401


def test_health_endpoint_is_public():
    response = client.get("/health")

    assert response.status_code == 200


def test_operator_can_login_and_access_protected_endpoint():
    email = os.getenv("TRAVELOPS_OPS_EMAIL", "ops@travelops360.com")
    password = os.getenv("TRAVELOPS_OPS_PASSWORD", "TravelOps@123")

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"

    token = login_data["access_token"]

    protected_response = client.get(
        "/summary",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert protected_response.status_code == 200