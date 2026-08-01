import pytest
from fastapi.testclient import TestClient

from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB
from main import app

client = TestClient(app)

pytestmark = pytest.mark.integration

@pytest.fixture
def payment_cleanup():
    db_connection = ConnectionDB()
    created_payment = {
        "payment_id": None
    }

    try:
        db_connection.connect()
    except Exception:
        pytest.skip("PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests.")

    yield created_payment

    if created_payment["payment_id"] is not None:
        # Tear down: delete the payment created during the test
        conn = db_connection.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM payments WHERE id = %s", (str(created_payment["payment_id"]),))
            conn.commit()

    db_connection.close()

def test_get_payment_endpoint_e2e(payment_cleanup: dict[str, str | None]):
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
