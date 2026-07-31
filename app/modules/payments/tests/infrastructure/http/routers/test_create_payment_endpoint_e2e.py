import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB

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


def test_create_payment_endpoint_e2e(payment_cleanup: dict[str, uuid.UUID | None]):
    created_payment = payment_cleanup

    data_request = {
        "amount": "100.00",
        "currency": "USD",
    }

    response = client.post("/api/v1/payments", json=data_request)

    assert response.status_code == 201

    created_id = response.json().get("id")
    created_payment["payment_id"] = uuid.UUID(created_id)  # Store the id so the fixture cleans it up
