import asyncio
import json
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import (
    PostgresPaymentRepository,
)
from app.shared.outbox.application.relay_outbox_batch_use_case import RelayOutboxBatchUseCase
from app.shared.outbox.domain.ports.outbox_store_port import ClaimedOutboxBatch
from app.shared.outbox.infrastructure.persistence.postgres_outbox_store import PostgresOutboxStore
from app.shared.outbox.infrastructure.publishing.logging_event_publisher import (
    LoggingEventPublisher,
)
from app.shared.persistence.postgres_connection import CONNINFO, ConnectionDB

pytestmark = pytest.mark.integration

# The dev database is shared and the relay claims ANY due pending row, so every row a test inserts
# is dated in the distant past: it sorts ahead of whatever else is pending, and a claim whose limit
# equals the number of rows inserted never reaches a row the test does not own.
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)

# Failing here means SKIP LOCKED is not in effect: the second claim would wait on A's row locks.
LOCK_WAIT_GUARD_SECONDS = 5

InsertRow = Callable[..., Awaitable[int]]
FetchRow = Callable[[int], Awaitable[dict[str, Any]]]


def long_ago(seconds: int) -> datetime:
    return LONG_AGO + timedelta(seconds=seconds)


async def sweep_stale_test_rows(pool: AsyncConnectionPool[AsyncConnection[TupleRow]]) -> None:
    # Rows left by an interrupted run. No real row is this old: available_at defaults to now().
    async with pool.connection() as conn:
        await conn.execute(
            "DELETE FROM payments WHERE id IN"
            " (SELECT aggregate_id FROM outbox WHERE available_at < '2001-01-01')"
        )
        await conn.execute("DELETE FROM outbox WHERE available_at < '2001-01-01'")


@pytest.fixture
async def pool() -> AsyncGenerator[AsyncConnectionPool[AsyncConnection[TupleRow]]]:
    # A pool of its own, bound to this test's event loop. max_size 3: the concurrency test holds
    # two claims open at once and still needs a connection for the assertions.
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]] = AsyncConnectionPool(
        CONNINFO, min_size=1, max_size=3, open=False
    )
    try:
        await pool.open(wait=True, timeout=3)
    except PoolTimeout:
        await pool.close()
        pytest.skip(
            "PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests."
        )
    await sweep_stale_test_rows(pool)
    yield pool
    await pool.close()


@pytest.fixture
async def store(
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]],
) -> PostgresOutboxStore:
    return PostgresOutboxStore(ConnectionDB(pool=pool))


@pytest.fixture
async def insert_row(
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]],
) -> AsyncGenerator[InsertRow]:
    inserted: list[int] = []

    async def insert(
        *,
        available_at: datetime,
        status: str = "pending",
        attempts: int = 0,
        payload: dict[str, Any] | None = None,
        event_id: uuid.UUID | None = None,
        aggregate_id: uuid.UUID | None = None,
    ) -> int:
        async with pool.connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO outbox"
                " (event_id, aggregate_type, aggregate_id, event_type, payload,"
                "  status, attempts, available_at)"
                " VALUES (%s, 'test', %s, 'test.event', %s, %s, %s, %s) RETURNING id",
                (
                    event_id or uuid.uuid4(),
                    aggregate_id or uuid.uuid4(),
                    Jsonb(payload if payload is not None else {}),
                    status,
                    attempts,
                    available_at,
                ),
            )
            row = await cursor.fetchone()
            assert row is not None
            inserted.append(row[0])
            return row[0]

    yield insert

    async with pool.connection() as conn:
        await conn.execute("DELETE FROM outbox WHERE id = ANY(%s)", (inserted,))


@pytest.fixture
async def fetch_row(pool: AsyncConnectionPool[AsyncConnection[TupleRow]]) -> FetchRow:
    async def fetch(message_id: int) -> dict[str, Any]:
        async with pool.connection() as conn:
            cursor = await conn.execute(
                "SELECT status, attempts, available_at, last_error, processed_at"
                " FROM outbox WHERE id = %s",
                (message_id,),
            )
            row = await cursor.fetchone()
            assert row is not None
            keys = ("status", "attempts", "available_at", "last_error", "processed_at")
            return dict(zip(keys, row, strict=True))

    return fetch


@pytest.fixture
async def db_clock(
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]],
) -> Callable[[], Awaitable[datetime]]:
    # The database's own clock, so timing assertions never depend on the test host's clock.
    async def read() -> datetime:
        async with pool.connection() as conn:
            cursor = await conn.execute("SELECT clock_timestamp()")
            row = await cursor.fetchone()
            assert row is not None
            return row[0]

    return read


class TestClaim:
    async def test_claims_only_pending_rows_that_are_due(
        self, store: PostgresOutboxStore, insert_row: InsertRow
    ):
        published = await insert_row(available_at=long_ago(1), status="published")
        failed = await insert_row(available_at=long_ago(2), status="failed")
        future = await insert_row(available_at=datetime.now(UTC) + timedelta(hours=1))
        due = await insert_row(available_at=long_ago(3))

        async with store.claim(4) as batch:
            claimed_ids = {m.id for m in batch.messages}

        assert claimed_ids & {published, failed, future, due} == {due}

    async def test_orders_by_available_at_then_id(
        self, store: PostgresOutboxStore, insert_row: InsertRow
    ):
        last = await insert_row(available_at=long_ago(3))
        first = await insert_row(available_at=long_ago(1))
        tie_low = await insert_row(available_at=long_ago(2))
        tie_high = await insert_row(available_at=long_ago(2))
        own = {last, first, tie_low, tie_high}

        async with store.claim(4) as batch:
            claimed_ids = [m.id for m in batch.messages if m.id in own]

        assert claimed_ids == [first, tie_low, tie_high, last]

    async def test_respects_the_limit(self, store: PostgresOutboxStore, insert_row: InsertRow):
        first = await insert_row(available_at=long_ago(1))
        second = await insert_row(available_at=long_ago(2))
        third = await insert_row(available_at=long_ago(3))

        async with store.claim(2) as batch:
            claimed = [m.id for m in batch.messages]

        # Only own ids are compared: the shared dev DB may hold rows the test does not own.
        assert len([i for i in claimed if i in {first, second, third}]) == 2
        assert [i for i in claimed if i in {first, second, third}] == [first, second]

    async def test_returns_the_payload_as_json_text_and_the_stored_attempts(
        self, store: PostgresOutboxStore, insert_row: InsertRow
    ):
        body = {"amount": "10.00", "currency": "USD", "items": [1, 2]}
        event_id = uuid.uuid4()
        aggregate_id = uuid.uuid4()
        message_id = await insert_row(
            available_at=long_ago(1),
            attempts=3,
            payload=body,
            event_id=event_id,
            aggregate_id=aggregate_id,
        )

        async with store.claim(1) as batch:
            [message] = batch.messages

        assert message.id == message_id
        assert message.event_id == event_id
        assert message.aggregate_id == aggregate_id
        assert isinstance(message.payload, str)
        assert json.loads(message.payload) == body
        assert message.attempts == 3
        assert message.aggregate_type == "test"
        assert message.event_type == "test.event"

    async def test_rejects_a_limit_below_one(self, store: PostgresOutboxStore):
        with pytest.raises(ValueError):
            async with store.claim(0):
                pass


class TestOutcomes:
    async def test_mark_published_sets_status_and_processed_at_together(
        self, store: PostgresOutboxStore, insert_row: InsertRow, fetch_row: FetchRow
    ):
        message_id = await insert_row(available_at=long_ago(1), attempts=2)

        async with store.claim(1) as batch:
            await batch.mark_published(message_id)

        row = await fetch_row(message_id)
        assert row["status"] == "published"
        assert row["processed_at"] is not None
        assert row["attempts"] == 2

    async def test_mark_published_stamps_the_moment_of_the_update_not_the_batch_start(
        self,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
        db_clock: Callable[[], Awaitable[datetime]],
    ):
        message_id = await insert_row(available_at=long_ago(1))
        before = await db_clock()

        async with store.claim(1) as batch:
            await asyncio.sleep(0.3)  # a slow publish: now() would still read the batch start
            await batch.mark_published(message_id)

        row = await fetch_row(message_id)
        assert row["processed_at"] >= before + timedelta(seconds=0.3)

    async def test_reschedule_increments_attempts_and_records_the_error_and_delay(
        self,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
        db_clock: Callable[[], Awaitable[datetime]],
    ):
        message_id = await insert_row(available_at=long_ago(1), attempts=1)
        before = await db_clock()

        async with store.claim(1) as batch:
            await batch.reschedule(message_id, delay_seconds=60, error="TimeoutError: slow")

        after = await db_clock()
        row = await fetch_row(message_id)
        assert row["status"] == "pending"
        assert row["attempts"] == 2
        assert row["last_error"] == "TimeoutError: slow"
        assert row["processed_at"] is None
        assert (
            before + timedelta(seconds=60) <= row["available_at"] <= after + timedelta(seconds=60)
        )

    async def test_reschedule_counts_the_delay_from_the_update_not_the_batch_start(
        self,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
        db_clock: Callable[[], Awaitable[datetime]],
    ):
        message_id = await insert_row(available_at=long_ago(1))
        before = await db_clock()

        async with store.claim(1) as batch:
            await asyncio.sleep(0.3)
            await batch.reschedule(message_id, delay_seconds=60, error="boom")

        row = await fetch_row(message_id)
        assert row["available_at"] >= before + timedelta(seconds=60.3)

    async def test_a_rescheduled_row_is_not_claimable_until_its_delay_passes(
        self, store: PostgresOutboxStore, insert_row: InsertRow
    ):
        message_id = await insert_row(available_at=long_ago(1))
        async with store.claim(1) as batch:
            await batch.reschedule(message_id, delay_seconds=3600, error="boom")

        async with store.claim(1) as batch:
            claimed_ids = [m.id for m in batch.messages]

        assert message_id not in claimed_ids

    async def test_mark_failed_sets_status_increments_attempts_and_keeps_processed_at_null(
        self, store: PostgresOutboxStore, insert_row: InsertRow, fetch_row: FetchRow
    ):
        message_id = await insert_row(available_at=long_ago(1), attempts=4)

        async with store.claim(1) as batch:
            await batch.mark_failed(message_id, error="RuntimeError: gave up")

        row = await fetch_row(message_id)
        assert row["status"] == "failed"
        assert row["attempts"] == 5
        assert row["last_error"] == "RuntimeError: gave up"
        assert row["processed_at"] is None

    async def test_an_exception_inside_the_block_rolls_every_outcome_back(
        self, store: PostgresOutboxStore, insert_row: InsertRow, fetch_row: FetchRow
    ):
        published = await insert_row(available_at=long_ago(1))
        rescheduled = await insert_row(available_at=long_ago(2), attempts=1)
        failed = await insert_row(available_at=long_ago(3), attempts=2)

        with pytest.raises(RuntimeError, match="crash mid-batch"):
            async with store.claim(3) as batch:
                await batch.mark_published(published)
                await batch.reschedule(rescheduled, delay_seconds=60, error="boom")
                await batch.mark_failed(failed, error="boom")
                raise RuntimeError("crash mid-batch")

        for message_id, attempts in ((published, 0), (rescheduled, 1), (failed, 2)):
            row = await fetch_row(message_id)
            assert row["status"] == "pending"
            assert row["attempts"] == attempts
            assert row["last_error"] is None
            assert row["processed_at"] is None


Outcome = Callable[[ClaimedOutboxBatch, int], Awaitable[None]]

OUTCOMES: dict[str, Outcome] = {
    "mark_published": lambda batch, i: batch.mark_published(i),
    "reschedule": lambda batch, i: batch.reschedule(i, delay_seconds=60, error="boom"),
    "mark_failed": lambda batch, i: batch.mark_failed(i, error="boom"),
}


@pytest.mark.parametrize("outcome", OUTCOMES.values(), ids=OUTCOMES.keys())
class TestBatchGuards:
    async def test_rejects_an_id_the_batch_did_not_claim(
        self,
        outcome: Outcome,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
    ):
        claimed = await insert_row(available_at=long_ago(1))
        # Not due, so never claimed, yet still a pending row the UPDATE could reach by id.
        unclaimed = await insert_row(available_at=datetime.now(UTC) + timedelta(hours=1))

        with pytest.raises(ValueError, match=str(unclaimed)):
            async with store.claim(1) as batch:
                assert [m.id for m in batch.messages] == [claimed]
                await outcome(batch, unclaimed)

        row = await fetch_row(unclaimed)
        assert (row["status"], row["attempts"], row["last_error"]) == ("pending", 0, None)

    async def test_a_second_outcome_for_the_same_id_fails_and_rolls_the_batch_back(
        self,
        outcome: Outcome,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
    ):
        first = await insert_row(available_at=long_ago(1))
        second = await insert_row(available_at=long_ago(2))

        with pytest.raises(RuntimeError, match=str(first)):
            async with store.claim(2) as batch:
                await batch.mark_published(second)
                await batch.mark_published(first)
                await outcome(batch, first)

        for message_id in (first, second):
            row = await fetch_row(message_id)
            assert (row["status"], row["attempts"], row["processed_at"]) == ("pending", 0, None)

    async def test_a_second_outcome_after_a_reschedule_also_fails(
        self,
        outcome: Outcome,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
    ):
        # A reschedule leaves the row 'pending', so the status predicate alone cannot catch this.
        message_id = await insert_row(available_at=long_ago(1))

        with pytest.raises(RuntimeError, match=str(message_id)):
            async with store.claim(1) as batch:
                await batch.reschedule(message_id, delay_seconds=60, error="boom")
                await outcome(batch, message_id)

        row = await fetch_row(message_id)
        assert (row["status"], row["attempts"], row["last_error"]) == ("pending", 0, None)

    async def test_the_batch_is_unusable_after_the_block(
        self,
        outcome: Outcome,
        store: PostgresOutboxStore,
        insert_row: InsertRow,
        fetch_row: FetchRow,
    ):
        message_id = await insert_row(available_at=long_ago(1))
        async with store.claim(1) as batch:
            pass

        with pytest.raises(RuntimeError, match="batch is closed"):
            await outcome(batch, message_id)

        row = await fetch_row(message_id)
        assert (row["status"], row["attempts"]) == ("pending", 0)

    async def test_the_batch_is_unusable_after_a_block_that_raised(
        self, outcome: Outcome, store: PostgresOutboxStore, insert_row: InsertRow
    ):
        message_id = await insert_row(available_at=long_ago(1))
        batches: list[ClaimedOutboxBatch] = []
        with pytest.raises(KeyError):
            async with store.claim(1) as batch:
                batches.append(batch)
                raise KeyError("crash")

        with pytest.raises(RuntimeError, match="batch is closed"):
            await outcome(batches[0], message_id)


class TestConcurrentClaims:
    async def test_a_second_claim_skips_rows_locked_by_an_open_claim(
        self, store: PostgresOutboxStore, insert_row: InsertRow, fetch_row: FetchRow
    ):
        first = await insert_row(available_at=long_ago(1))
        second = await insert_row(available_at=long_ago(2))
        third = await insert_row(available_at=long_ago(3))

        async with store.claim(2) as claim_a:
            assert [m.id for m in claim_a.messages] == [first, second]

            # B runs while A is still open, on a second pooled connection. Without SKIP LOCKED it
            # would wait on A's locks, so the guard turns a hang into a failure.
            async with asyncio.timeout(LOCK_WAIT_GUARD_SECONDS):
                async with store.claim(1) as claim_b:
                    assert [m.id for m in claim_b.messages] == [third]

            await claim_a.mark_published(first)
            await claim_a.mark_failed(second, error="boom")

        # A has committed: its resolved rows are no longer claimable.
        async with store.claim(3) as claim_c:
            claimed_ids = [m.id for m in claim_c.messages]
        assert first not in claimed_ids
        assert second not in claimed_ids
        assert third in claimed_ids
        assert (await fetch_row(first))["status"] == "published"
        assert (await fetch_row(second))["status"] == "failed"


class TestFullFlow:
    async def test_a_created_payment_ends_with_its_outbox_row_published(
        self, pool: AsyncConnectionPool[AsyncConnection[TupleRow]], store: PostgresOutboxStore
    ):
        payment = Payment.create(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            amount=Money(amount=Decimal("42.00"), currency="USD"),
            event_id=uuid.uuid4(),
        )
        repo = PostgresPaymentRepository(connection=ConnectionDB(pool=pool))

        try:
            await repo.create_payment(payment)
            async with pool.connection() as conn:
                # The relay claims any due row, so this one is dated ahead of the rest and the
                # batch size of 1 keeps foreign pending rows untouched.
                cursor = await conn.execute(
                    "UPDATE outbox SET available_at = %s WHERE aggregate_id = %s",
                    (long_ago(-86400 * 365), payment.id),
                )
                # Guards the premise: with no row of its own, the relay would publish a foreign one.
                assert cursor.rowcount == 1

            use_case = RelayOutboxBatchUseCase(
                store,
                LoggingEventPublisher(),
                batch_size=1,
                max_attempts=3,
                publish_timeout_seconds=5,
                backoff=lambda attempts: 1.0,
            )
            relayed = await use_case.execute()

            async with pool.connection() as conn:
                cursor = await conn.execute(
                    "SELECT status, attempts, processed_at, event_type FROM outbox"
                    " WHERE aggregate_id = %s",
                    (payment.id,),
                )
                rows = await cursor.fetchall()
        finally:
            async with pool.connection() as conn:
                await conn.execute("DELETE FROM payments WHERE id = %s", (payment.id,))
                await conn.execute("DELETE FROM outbox WHERE aggregate_id = %s", (payment.id,))

        assert relayed == 1
        assert len(rows) == 1
        status, attempts, processed_at, event_type = rows[0]
        assert event_type == "payment.created"
        assert status == "published"
        assert attempts == 0
        assert processed_at is not None
