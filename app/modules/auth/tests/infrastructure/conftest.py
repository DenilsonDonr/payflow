import uuid

import psycopg
import pytest

from app.shared.persistence.postgres_connection import CONNINFO

POSTGRES_DOWN = "PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests."


@pytest.fixture
async def user_cleanup():
    """Yield an email unique to this test, and delete the user registered with it afterwards."""
    try:
        # A connection of its own, not the app's pool: this fixture runs on pytest's event loop.
        conn = await psycopg.AsyncConnection.connect(CONNINFO)
    except psycopg.OperationalError:
        pytest.skip(POSTGRES_DOWN)

    email = f"{uuid.uuid4()}@example.com"

    yield email

    async with conn:
        await conn.execute("DELETE FROM users WHERE lower(email) = %s", (email,))
