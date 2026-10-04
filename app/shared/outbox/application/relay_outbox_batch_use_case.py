import asyncio
import math
from collections.abc import Callable

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.event_publisher_port import EventPublisherPort
from app.shared.outbox.domain.ports.outbox_store_port import ClaimedOutboxBatch, OutboxStorePort

# Keeps one pathological exception message from bloating the `last_error` column.
MAX_ERROR_LENGTH = 1000


class RelayOutboxBatchUseCase:
    def __init__(
        self,
        store: OutboxStorePort,
        publisher: EventPublisherPort,
        *,
        batch_size: int,
        max_attempts: int,
        publish_timeout_seconds: float,
        backoff: Callable[[int], float],
    ) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        if not math.isfinite(publish_timeout_seconds) or publish_timeout_seconds <= 0:
            raise ValueError(
                f"publish_timeout_seconds must be finite and > 0, got {publish_timeout_seconds}"
            )
        self._store = store
        self._publisher = publisher
        self._batch_size = batch_size
        self._max_attempts = max_attempts
        self._publish_timeout_seconds = publish_timeout_seconds
        self._backoff = backoff

    async def execute(self) -> int:
        async with self._store.claim(self._batch_size) as batch:
            for message in batch.messages:
                await self._relay(batch, message)
            return len(batch.messages)

    async def _relay(self, batch: ClaimedOutboxBatch, message: OutboxMessage) -> None:
        try:
            async with asyncio.timeout(self._publish_timeout_seconds):
                await self._publisher.publish(message)
        # Exception, never BaseException: a CancelledError (shutdown) must escape
        # the claim block so the whole batch rolls back and stays pending.
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LENGTH]
            if message.attempts + 1 >= self._max_attempts:
                await batch.mark_failed(message.id, error=error)
            else:
                await batch.reschedule(
                    message.id, delay_seconds=self._backoff(message.attempts), error=error
                )
        else:
            await batch.mark_published(message.id)
