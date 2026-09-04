import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_get_payment_endpoint_e2e(client: TestClient, payment_cleanup: dict[str, str | None]):
    created_payment = payment_cleanup

    create_data_request = {
        "amount": "100.00",
        "currency": "USD",
    }

    create_response = client.post("/api/v1/payments", json=create_data_request)

    assert create_response.status_code == 201

    # Store the id so the fixture cleans it up
    created_payment["payment_id"] = create_response.json().get("id")

    get_response = client.get(f"/api/v1/payments/{create_response.json().get('id')}")

    assert get_response.status_code == 200
    assert get_response.json().get("amount") == create_response.json().get("amount")
    assert get_response.json().get("currency") == create_response.json().get("currency")
