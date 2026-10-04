from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import replace

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.outbox_store_port import ClaimedOutboxBatch, OutboxStorePort


class InMemoryClaimedBatch(ClaimedOutboxBatch):
    """Buffers outcomes so the store can apply them only on commit."""

    def __init__(self, messages: list[OutboxMessage]) -> None:
        self._messages = messages
        self.published: list[int] = []
        self.rescheduled: dict[int, tuple[float, str]] = {}
        self.failed: dict[int, str] = {}

    @property
    def messages(self) -> list[OutboxMessage]:
        return self._messages

    async def mark_published(self, message_id: int) -> None:
        self.published.append(message_id)

    async def reschedule(self, message_id: int, *, delay_seconds: float, error: str) -> None:
        self.rescheduled[message_id] = (delay_seconds, error)

    async def mark_failed(self, message_id: int, *, error: str) -> None:
        self.failed[message_id] = error


class InMemoryOutboxStore(OutboxStorePort):
    """Pending means "not yet published or failed"; a rescheduled row stays claimable.

    Backoff timing is not simulated: a rescheduled row is recorded but is
    claimable again immediately, which is enough for use-case unit tests.
    A rescheduled row does come back with `attempts + 1`, like the real store.
    """

    def __init__(self, messages: list[OutboxMessage]) -> None:
        self._pending: list[OutboxMessage] = list(messages)
        self.published: list[int] = []
        self.rescheduled: dict[int, tuple[float, str]] = {}
        self.failed: dict[int, str] = {}
        self.commits = 0
        self.rollbacks = 0

    def claim(self, limit: int) -> AbstractAsyncContextManager[ClaimedOutboxBatch]:
        return self._claim(limit)

    @asynccontextmanager
    async def _claim(self, limit: int) -> AsyncGenerator[ClaimedOutboxBatch]:
        batch = InMemoryClaimedBatch(self._pending[:limit])
        try:
            yield batch
        except BaseException:
            self.rollbacks += 1
            raise
        self._commit(batch)

    def _commit(self, batch: InMemoryClaimedBatch) -> None:
        self.commits += 1
        self.published.extend(batch.published)
        self.rescheduled.update(batch.rescheduled)
        self.failed.update(batch.failed)
        resolved = set(batch.published) | set(batch.failed)
        # Without the increment the relay's retry ceiling never triggers.
        self._pending = [
            replace(m, attempts=m.attempts + 1) if m.id in batch.rescheduled else m
            for m in self._pending
            if m.id not in resolved
        ]
