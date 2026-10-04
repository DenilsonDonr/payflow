import asyncio
import uuid

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.event_publisher_port import EventPublisherPort


class FakeEventPublisher(EventPublisherPort):
    """Succeeds by default; per `event_id` it can be told to raise or to hang."""

    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []
        self._failures: dict[uuid.UUID, Exception] = {}
        self._hanging: set[uuid.UUID] = set()

    def fail_with(self, event_id: uuid.UUID, error: Exception) -> None:
        self._failures[event_id] = error

    def hang_on(self, event_id: uuid.UUID) -> None:
        self._hanging.add(event_id)

    async def publish(self, message: OutboxMessage) -> None:
        if message.event_id in self._hanging:
            # Never set: the caller's asyncio.timeout is what ends the wait.
            await asyncio.Event().wait()
        if message.event_id in self._failures:
            raise self._failures[message.event_id]
        self.published.append(message)
