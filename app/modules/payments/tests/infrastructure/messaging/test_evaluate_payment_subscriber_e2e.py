import pytest
from fastapi.testclient import TestClient

from app.modules.payments.domain.entities.payment import PaymentState
from main import app

client = TestClient(app)

pytestmark = pytest.mark.integration


class TestEvaluatePaymentE2E:
    # The bus is synchronous, so by the time the POST returns fraud has already published its
    # verdict and the payment has been evaluated. The GET is what shows the resulting state.
    def test_payment_below_the_fraud_threshold_ends_up_approved(
        self, payment_cleanup: dict[str, str | None]
    ) -> None:
        created_payment = payment_cleanup

        data_request = {
            "amount": "100.00",
            "currency": "USD",
        }

        response = client.post("/api/v1/payments", json=data_request)

        assert response.status_code == 201

        id = response.json().get("id")
        created_payment["payment_id"] = id  # Store the id so the fixture cleans it up

        get_response = client.get(f"/api/v1/payments/{id}")

        assert get_response.status_code == 200
        assert get_response.json().get("state") == PaymentState.APPROVED.value

    def test_payment_above_the_fraud_threshold_ends_up_rejected(
        self, payment_cleanup: dict[str, str | None]
    ) -> None:
        created_payment = payment_cleanup

        data_request = {
            "amount": "1500.00",
            "currency": "USD",
        }

        response = client.post("/api/v1/payments", json=data_request)

        assert response.status_code == 201

        id = response.json().get("id")
        created_payment["payment_id"] = id  # Store the id so the fixture cleans it up

        get_response = client.get(f"/api/v1/payments/{id}")

        assert get_response.status_code == 200
        assert get_response.json().get("state") == PaymentState.REJECTED.value
