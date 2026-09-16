import psycopg
import pytest

from app.shared.persistence.postgres_connection import CONNINFO

POSTGRES_DOWN = "PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests."


@pytest.fixture
async def payment_cleanup():
    created_payment = {
        "payment_id": None,
    }

    try:
        # A connection of its own, not the app's pool: this fixture runs on pytest's event loop
        # and the pool belongs to the TestClient's. It is also what turns an unreachable
        # database into a skip.
        conn = await psycopg.AsyncConnection.connect(CONNINFO)
    except psycopg.OperationalError:
        pytest.skip(POSTGRES_DOWN)

    yield created_payment

    # Tear down: delete the payment created during the test
    async with conn:
        if created_payment["payment_id"] is not None:
            await conn.execute(
                "DELETE FROM payments WHERE id = %s", (str(created_payment["payment_id"]),)
            )
