import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_create_payment_endpoint_e2e(
    client: TestClient, payment_cleanup: dict[str, uuid.UUID | None]
):
    created_payment = payment_cleanup

    data_request = {
        "amount": "100.00",
        "currency": "USD",
    }

    response = client.post("/api/v1/payments", json=data_request)

    assert response.status_code == 201

    created_id = response.json().get("id")
    created_payment["payment_id"] = uuid.UUID(created_id)  # Store the id so the fixture cleans it up
