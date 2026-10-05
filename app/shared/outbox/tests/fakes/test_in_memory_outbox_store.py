import re
import uuid
from collections.abc import Awaitable, Callable

import pytest

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.outbox_store_port import ClaimedOutboxBatch
from app.shared.outbox.tests.fakes.in_memory_outbox_store import InMemoryOutboxStore


def make_message(message_id: int) -> OutboxMessage:
    return OutboxMessage(
        id=message_id,
        event_id=uuid.uuid4(),
        aggregate_type="payment",
        aggregate_id=uuid.uuid4(),
        event_type="payment.created",
        payload="{}",
        attempts=0,
    )


async def claimed_ids(store: InMemoryOutboxStore, limit: int = 100) -> list[int]:
    async with store.claim(limit) as batch:
        return [m.id for m in batch.messages]


class TestInMemoryOutboxStoreCommit:
    async def test_normal_exit_applies_every_outcome_and_counts_one_commit(self):
        store = InMemoryOutboxStore([make_message(1), make_message(2), make_message(3)])

        async with store.claim(10) as batch:
            await batch.mark_published(1)
            await batch.reschedule(2, delay_seconds=7.5, error="boom")
            await batch.mark_failed(3, error="dead")

        assert store.published == [1]
        assert store.rescheduled == {2: (7.5, "boom")}
        assert store.failed == {3: "dead"}
        assert store.commits == 1
        assert store.rollbacks == 0

    async def test_published_and_failed_rows_leave_pending_but_rescheduled_stay_claimable(self):
        store = InMemoryOutboxStore([make_message(1), make_message(2), make_message(3)])

        async with store.claim(10) as batch:
            await batch.mark_published(1)
            await batch.reschedule(2, delay_seconds=1.0, error="boom")
            await batch.mark_failed(3, error="dead")

        assert await claimed_ids(store) == [2]

    async def test_rescheduled_row_is_reclaimed_with_attempts_incremented_by_one(self):
        # The real store increments `attempts` in SQL; the relay's retry ceiling
        # only terminates because of it, so the fake must model it too.
        store = InMemoryOutboxStore([make_message(1)])

        async with store.claim(10) as batch:
            await batch.reschedule(1, delay_seconds=1.0, error="boom")

        async with store.claim(10) as batch:
            assert [(m.id, m.attempts) for m in batch.messages] == [(1, 1)]

    async def test_claim_returns_at_most_limit_messages_in_order(self):
        store = InMemoryOutboxStore([make_message(i) for i in range(1, 6)])

        assert await claimed_ids(store, limit=2) == [1, 2]


class TestInMemoryOutboxStoreRollback:
    async def test_exception_inside_the_block_counts_a_rollback_and_applies_nothing(self):
        store = InMemoryOutboxStore([make_message(1), make_message(2)])

        with pytest.raises(RuntimeError):
            async with store.claim(10) as batch:
                await batch.mark_published(1)
                await batch.reschedule(2, delay_seconds=1.0, error="boom")
                raise RuntimeError("crash mid-batch")

        assert store.published == []
        assert store.rescheduled == {}
        assert store.failed == {}
        assert store.rollbacks == 1
        assert store.commits == 0

    async def test_rows_stay_pending_after_a_rollback(self):
        store = InMemoryOutboxStore([make_message(1), make_message(2)])

        with pytest.raises(RuntimeError):
            async with store.claim(10) as batch:
                await batch.mark_published(1)
                await batch.mark_failed(2, error="dead")
                raise RuntimeError("crash mid-batch")

        assert await claimed_ids(store) == [1, 2]


Outcome = Callable[[ClaimedOutboxBatch, int], Awaitable[None]]

OUTCOMES: dict[str, Outcome] = {
    "mark_published": lambda batch, i: batch.mark_published(i),
    "reschedule": lambda batch, i: batch.reschedule(i, delay_seconds=1.0, error="boom"),
    "mark_failed": lambda batch, i: batch.mark_failed(i, error="dead"),
}


@pytest.mark.parametrize("outcome", OUTCOMES.values(), ids=OUTCOMES.keys())
class TestInMemoryBatchGuards:
    async def test_rejects_an_id_the_batch_did_not_claim(self, outcome: Outcome):
        store = InMemoryOutboxStore([make_message(1), make_message(2)])

        with pytest.raises(ValueError, match=r"^outbox message 2 was not claimed by this batch$"):
            async with store.claim(1) as batch:
                await outcome(batch, 2)

    async def test_a_second_outcome_for_the_same_id_fails_and_rolls_back(self, outcome: Outcome):
        store = InMemoryOutboxStore([make_message(1)])

        with pytest.raises(
            RuntimeError, match=r"^outbox message 1 already has an outcome in this batch$"
        ):
            async with store.claim(1) as batch:
                await batch.mark_published(1)
                await outcome(batch, 1)

        assert store.published == []
        assert store.rollbacks == 1

    async def test_the_batch_is_unusable_after_the_block(self, outcome: Outcome):
        store = InMemoryOutboxStore([make_message(1)])
        async with store.claim(1) as batch:
            pass

        with pytest.raises(
            RuntimeError,
            match=re.escape("the outbox batch is closed: its claim block has already exited"),
        ):
            await outcome(batch, 1)
