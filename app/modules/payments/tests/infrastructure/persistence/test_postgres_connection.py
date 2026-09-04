import pytest
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.modules.payments.infrastructure.persistence.postgres_connection import (
    CONNINFO,
    ConnectionDB,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def single_connection_db():
    """A pool of exactly one connection: borrowing twice only works if the first was given back."""
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]] = AsyncConnectionPool(
        CONNINFO, min_size=1, max_size=1, open=False
    )

    try:
        await pool.open(wait=True, timeout=3)
    except PoolTimeout:
        await pool.close()
        pytest.skip("PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests.")

    yield ConnectionDB(pool=pool)

    await pool.close()


class TestConnectionDB:
    async def test_borrows_a_working_connection(self, single_connection_db: ConnectionDB):
        async with single_connection_db.connection() as conn, conn.cursor() as cursor:
            await cursor.execute("SELECT 1")
            assert await cursor.fetchone() == (1,)

    async def test_returns_the_connection_when_the_block_ends(
        self, single_connection_db: ConnectionDB
    ):
        async with single_connection_db.connection() as conn, conn.cursor() as cursor:
            await cursor.execute("SELECT 1")

        # The only connection in the pool. Held onto, this would raise PoolTimeout.
        async with single_connection_db.connection() as conn, conn.cursor() as cursor:
            await cursor.execute("SELECT 1")
            assert await cursor.fetchone() == (1,)

    async def test_returns_the_connection_even_when_the_block_raises(
        self, single_connection_db: ConnectionDB
    ):
        with pytest.raises(RuntimeError):
            async with single_connection_db.connection() as conn:
                await conn.execute("SELECT 1")
                raise RuntimeError("the caller blew up mid-transaction")

        async with single_connection_db.connection() as conn, conn.cursor() as cursor:
            await cursor.execute("SELECT 1")
            assert await cursor.fetchone() == (1,)

    async def test_rolls_back_what_a_failing_block_wrote(self, single_connection_db: ConnectionDB):
        payment_id = "rollback-probe"

        with pytest.raises(RuntimeError):
            async with single_connection_db.connection() as conn:
                await conn.execute(
                    "INSERT INTO payments (id, amount, currency, state) VALUES (%s, %s, %s, %s)",
                    (payment_id, 1, "USD", "pending"),
                )
                raise RuntimeError("the caller blew up after writing")

        async with single_connection_db.connection() as conn, conn.cursor() as cursor:
            await cursor.execute("SELECT count(*) FROM payments WHERE id = %s", (payment_id,))
            assert await cursor.fetchone() == (0,)
