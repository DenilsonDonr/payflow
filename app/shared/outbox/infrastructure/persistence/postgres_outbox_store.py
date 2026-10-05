from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import LiteralString

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

# Every outcome UPDATE also requires status = 'pending', so a row that already has an outcome in
# this batch (or was resolved elsewhere) is never rewritten; the caller checks rowcount == 1.
_MARK_PUBLISHED_SQL = (
    "UPDATE outbox SET status = 'published', processed_at = clock_timestamp()"
    " WHERE id = %s AND status = 'pending'"
)

_RESCHEDULE_SQL = (
    "UPDATE outbox SET attempts = attempts + 1,"
    " available_at = clock_timestamp() + make_interval(secs => %s),"
    " last_error = %s"
    " WHERE id = %s AND status = 'pending'"
)

_MARK_FAILED_SQL = (
    "UPDATE outbox SET status = 'failed', attempts = attempts + 1, last_error = %s"
    " WHERE id = %s AND status = 'pending'"
)


class PostgresClaimedOutboxBatch(ClaimedOutboxBatch):
    """Outcomes are written on the claim's own connection, so they share its transaction.

    Misuse raises instead of writing: raising inside the claim block rolls the whole batch back,
    which is the right response to a programming error.
    """

    def __init__(self, conn: AsyncConnection[TupleRow], messages: list[OutboxMessage]):
        self._conn: AsyncConnection[TupleRow] | None = conn
        self._messages = messages
        self._claimed_ids = {m.id for m in messages}
        self._resolved_ids: set[int] = set()

    @property
    def messages(self) -> list[OutboxMessage]:
        return self._messages

    def close(self) -> None:
        # The connection goes back to the pool when the claim block exits; a late outcome would
        # otherwise run inside someone else's transaction.
        self._conn = None

    async def mark_published(self, message_id: int) -> None:
        await self._record(_MARK_PUBLISHED_SQL, (message_id,), message_id)

    async def reschedule(self, message_id: int, *, delay_seconds: float, error: str) -> None:
        await self._record(_RESCHEDULE_SQL, (delay_seconds, error, message_id), message_id)

    async def mark_failed(self, message_id: int, *, error: str) -> None:
        await self._record(_MARK_FAILED_SQL, (error, message_id), message_id)

    async def _record(
        self, sql: LiteralString, params: tuple[object, ...], message_id: int
    ) -> None:
        if self._conn is None:
            raise RuntimeError("the outbox batch is closed: its claim block has already exited")
        if message_id not in self._claimed_ids:
            raise ValueError(f"outbox message {message_id} was not claimed by this batch")
        # Tracked here, not only in SQL: a reschedule leaves the row 'pending', so the status
        # predicate alone would let a second outcome through.
        if message_id in self._resolved_ids:
            raise RuntimeError(f"outbox message {message_id} already has an outcome in this batch")
        # Recorded before the await: two overlapping calls would otherwise both pass the check.
        self._resolved_ids.add(message_id)

        cursor = await self._conn.execute(sql, params)
        if cursor.rowcount != 1:
            # Defence in depth: the row is locked by this transaction, so this only fires for a
            # row resolved outside this batch.
            raise RuntimeError(
                f"outbox message {message_id} is no longer pending:"
                " it was resolved outside this batch"
            )


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
            batch = PostgresClaimedOutboxBatch(conn, messages)
            try:
                yield batch
            finally:
                batch.close()
