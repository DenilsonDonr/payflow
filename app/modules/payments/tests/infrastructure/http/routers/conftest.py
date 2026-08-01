import pytest

from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB


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
