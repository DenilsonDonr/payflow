import psycopg
import pytest
from fastapi.testclient import TestClient

from app.modules.payments.infrastructure.persistence.postgres_connection import CONNINFO
from main import app

POSTGRES_DOWN = "PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests."


@pytest.fixture(scope="session")
def client():
    """One client for the whole session, entered as a context manager on purpose.

    Outside one, TestClient spins a fresh event loop per request; the app's async pool, opened on
    the first request, would then belong to a loop that is already gone by the second. The context
    manager also runs the lifespan, so the pool opens and closes where the app says it should.
    """
    with TestClient(app) as test_client:
        yield test_client


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
