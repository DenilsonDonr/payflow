import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

load_dotenv()

user = os.environ["POSTGRES_USER"]
password = os.environ["POSTGRES_PASSWORD"]
database = os.environ["POSTGRES_DB"]
host = os.environ["POSTGRES_HOST"]
port = os.environ["POSTGRES_PORT"]

CONNINFO = f"dbname={database} user={user} password={password} host={host} port={port}"

# max_size bounds how many requests can be inside the database at once; the rest wait on the pool
# rather than on Postgres. The event loop is free while they wait.
POOL_MIN_SIZE = int(os.environ.get("POSTGRES_POOL_MIN_SIZE", "4"))
POOL_MAX_SIZE = int(os.environ.get("POSTGRES_POOL_MAX_SIZE", "20"))

# Left closed on import: importing this module must not require a running database, or the unit
# tests that never touch Postgres would drag a pool of failing background workers behind them.
# An async pool also cannot be opened at construction time — psycopg needs a running event loop.
_pool: AsyncConnectionPool[AsyncConnection[TupleRow]] = AsyncConnectionPool(
    CONNINFO,
    min_size=POOL_MIN_SIZE,
    max_size=POOL_MAX_SIZE,
    check=AsyncConnectionPool.check_connection,
    open=False,
)


async def open_pool() -> None:
    """Start the pool. Idempotent, and does not block on the database being reachable."""
    await _pool.open()


async def close_pool() -> None:
    """Release every connection the pool holds. For shutdown: a pool cannot be reopened."""
    await _pool.close()


class ConnectionDB:
    """Hands out connections from the shared pool.

    Still a collaborator the repository receives rather than a module-level pool it reaches for,
    so a test can pass a pool of its own.
    """

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[TupleRow]] | None = None):
        self.pool = pool if pool is not None else _pool

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[AsyncConnection[TupleRow]]:
        """Borrow a connection for the duration of the block.

        Leaving the block commits (or rolls back, if the block raised) and returns the connection
        to the pool. A borrow that outlives its block would starve the pool, so there is no way
        to get a connection without a scope that gives it back.
        """
        await self.pool.open()  # idempotent, and what carries tests and scripts that skip lifespan
        async with self.pool.connection() as conn:
            yield conn
