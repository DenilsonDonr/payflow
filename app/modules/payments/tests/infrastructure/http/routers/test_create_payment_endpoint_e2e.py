import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.modules.payments.tests.infrastructure.conftest import POSTGRES_DOWN
from app.shared.persistence.postgres_connection import CONNINFO

pytestmark = pytest.mark.integration


def test_create_payment_endpoint_e2e(
    client: TestClient, payment_cleanup: dict[str, uuid.UUID | None]
):
    created_payment = payment_cleanup

    data_request = {
        "user_id": str(uuid.uuid4()),
        "amount": "100.00",
        "currency": "USD",
    }

    response = client.post("/api/v1/payments", json=data_request)

    assert response.status_code == 201

    created_id = response.json().get("id")
    created_payment["payment_id"] = uuid.UUID(
        created_id
    )  # Store the id so the fixture cleans it up


def test_create_payment_endpoint_e2e_leaves_one_pending_outbox_row(
    client: TestClient, payment_cleanup: dict[str, uuid.UUID | None]
):
    created_payment = payment_cleanup

    data_request = {
        "user_id": str(uuid.uuid4()),
        "amount": "100.00",
        "currency": "USD",
    }

    response = client.post("/api/v1/payments", json=data_request)

    assert response.status_code == 201

    payment_id = uuid.UUID(response.json()["id"])
    created_payment["payment_id"] = payment_id  # Store the id so the fixture cleans it up

    # The test is a plain def because it drives the sync TestClient, so the assertion uses psycopg's
    # sync connection. It is still a connection of its own, never the app's pool, which is bound to
    # the TestClient's event loop.
    try:
        conn = psycopg.connect(CONNINFO)
    except psycopg.OperationalError:
        pytest.skip(POSTGRES_DOWN)

    with conn:
        rows = conn.execute(
            "SELECT aggregate_id, aggregate_type, event_type, status FROM outbox "
            "WHERE aggregate_id = %s",
            (payment_id,),
        ).fetchall()

    assert rows == [(payment_id, "payment", "payment.created", "pending")]
