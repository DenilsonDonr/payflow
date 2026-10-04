from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.outbox_store_port import ClaimedOutboxBatch, OutboxStorePort
from app.shared.persistence.postgres_connection import ConnectionDB

# now() is the transaction's start, which here is the claim; a batch can stay open for seconds
# while it publishes. The claim's `available_at <= now()` is fine with that, but the UPDATEs use
# clock_timestamp() so processed_at and the backoff delay are not shortened by the batch's age.
_CLAIM_SQL = (
    "SELECT id, event_id, aggregate_type, aggregate_id, event_type, payload::text, attempts"
    " FROM outbox"
    " WHERE status = 'pending' AND available_at <= now()"
    " ORDER BY available_at, id"
    " LIMIT %s"
    " FOR UPDATE SKIP LOCKED"
)

_MARK_PUBLISHED_SQL = (
    "UPDATE outbox SET status = 'published', processed_at = clock_timestamp() WHERE id = %s"
)

_RESCHEDULE_SQL = (
    "UPDATE outbox SET attempts = attempts + 1,"
    " available_at = clock_timestamp() + make_interval(secs => %s),"
    " last_error = %s"
    " WHERE id = %s"
)

_MARK_FAILED_SQL = (
    "UPDATE outbox SET status = 'failed', attempts = attempts + 1, last_error = %s WHERE id = %s"
)


class PostgresClaimedOutboxBatch(ClaimedOutboxBatch):
    """Outcomes are written on the claim's own connection, so they share its transaction."""

    def __init__(self, conn: AsyncConnection[TupleRow], messages: list[OutboxMessage]):
        self._conn = conn
        self._messages = messages

    @property
    def messages(self) -> list[OutboxMessage]:
        return self._messages

    async def mark_published(self, message_id: int) -> None:
        await self._conn.execute(_MARK_PUBLISHED_SQL, (message_id,))

    async def reschedule(self, message_id: int, *, delay_seconds: float, error: str) -> None:
        await self._conn.execute(_RESCHEDULE_SQL, (delay_seconds, error, message_id))

    async def mark_failed(self, message_id: int, *, error: str) -> None:
        await self._conn.execute(_MARK_FAILED_SQL, (error, message_id))


class PostgresOutboxStore(OutboxStorePort):
    def __init__(self, connection: ConnectionDB):
        self._connection = connection

    @asynccontextmanager
    async def claim(self, limit: int) -> AsyncGenerator[ClaimedOutboxBatch]:
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")

        # One borrowed connection for the whole block: the row locks live as long as this
        # transaction, and leaving the block commits every outcome (an exception rolls it back).
        async with self._connection.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(_CLAIM_SQL, (limit,))
                rows = await cursor.fetchall()

            messages = [
                OutboxMessage(
                    id=row[0],
                    event_id=row[1],
                    aggregate_type=row[2],
                    aggregate_id=row[3],
                    event_type=row[4],
                    payload=row[5],
                    attempts=row[6],
                )
                for row in rows
            ]
            yield PostgresClaimedOutboxBatch(conn, messages)
