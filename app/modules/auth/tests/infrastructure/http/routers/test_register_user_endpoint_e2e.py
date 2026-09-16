import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_register_user_endpoint_e2e(client: TestClient, user_cleanup: str):
    email = user_cleanup

    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correct horse battery"}
    )

    assert response.status_code == 201
    assert response.json()["email"] == email


def test_register_user_endpoint_e2e_taken_email(client: TestClient, user_cleanup: str):
    data_request = {"email": user_cleanup, "password": "correct horse battery"}
    client.post("/api/v1/auth/register", json=data_request)

    response = client.post("/api/v1/auth/register", json=data_request)

    assert response.status_code == 400
