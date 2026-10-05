import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import pytest

from app.shared.outbox.application.relay_outbox_batch_use_case import RelayOutboxBatchUseCase
from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.outbox_store_port import ClaimedOutboxBatch, OutboxStorePort
from app.shared.outbox.tests.fakes.fake_event_publisher import FakeEventPublisher
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


class PublishedFailsBatch(ClaimedOutboxBatch):
    """Delegates to a real fake batch, but recording a publish outcome raises (a DB error)."""

    def __init__(self, inner: ClaimedOutboxBatch) -> None:
        self._inner = inner

    @property
    def messages(self) -> list[OutboxMessage]:
        return self._inner.messages

    async def mark_published(self, message_id: int) -> None:
        raise ConnectionError("lost connection while recording the outcome")

    async def reschedule(self, message_id: int, *, delay_seconds: float, error: str) -> None:
        await self._inner.reschedule(message_id, delay_seconds=delay_seconds, error=error)

    async def mark_failed(self, message_id: int, *, error: str) -> None:
        await self._inner.mark_failed(message_id, error=error)


class StoreWhoseMarkPublishedRaises(OutboxStorePort):
    """Wraps the in-memory store so its rollback/commit accounting stays the real one."""

    def __init__(self, inner: InMemoryOutboxStore) -> None:
        self._inner = inner

    def claim(self, limit: int) -> AbstractAsyncContextManager[ClaimedOutboxBatch]:
        return self._claim(limit)

    @asynccontextmanager
    async def _claim(self, limit: int) -> AsyncGenerator[ClaimedOutboxBatch]:
        async with self._inner.claim(limit) as batch:
            yield PublishedFailsBatch(batch)


def build_use_case(
    store: OutboxStorePort, publisher: FakeEventPublisher, *, timeout: float = 1.0
) -> RelayOutboxBatchUseCase:
    return RelayOutboxBatchUseCase(
        store,
        publisher,
        batch_size=10,
        max_attempts=5,
        publish_timeout_seconds=timeout,
        backoff=lambda attempts: 1.0,
    )


class TestRelayOutboxBatchUseCaseCancellation:
    async def test_cancelling_a_hanging_publish_rolls_the_batch_back(self):
        messages = [make_message(1), make_message(2)]
        store = InMemoryOutboxStore(messages)
        publisher = FakeEventPublisher()
        publisher.hang_on(messages[0].event_id)
        # Long timeout: the cancellation, not asyncio.timeout, must be what ends the wait.
        use_case = build_use_case(store, publisher, timeout=60.0)
        task = asyncio.create_task(use_case.execute())
        await asyncio.sleep(0.01)  # let it claim and block inside publish

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
        assert store.rollbacks == 1
        assert store.commits == 0
        assert store.published == []
        assert store.rescheduled == {}
        assert store.failed == {}


class TestRelayOutboxBatchUseCaseOutcomeRecordingFailure:
    async def test_a_failing_mark_published_propagates_and_rolls_the_batch_back(self):
        inner = InMemoryOutboxStore([make_message(1), make_message(2)])
        publisher = FakeEventPublisher()
        use_case = build_use_case(StoreWhoseMarkPublishedRaises(inner), publisher)

        with pytest.raises(ConnectionError):
            await use_case.execute()

        assert inner.rollbacks == 1
        assert inner.commits == 0
        assert inner.published == []
        assert inner.rescheduled == {}
        assert inner.failed == {}
