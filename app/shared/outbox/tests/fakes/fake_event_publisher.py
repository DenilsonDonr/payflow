import asyncio
import uuid

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.event_publisher_port import EventPublisherPort

# Upper bound for a hang nobody cuts: long enough to outlive any test timeout,
# short enough that a test that forgot one fails instead of stalling the suite.
HANG_GUARD_SECONDS = 5.0


class FakeEventPublisher(EventPublisherPort):
    """Succeeds by default; per `event_id` it can be told to raise or to hang."""

    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []
        self._failures: dict[uuid.UUID, BaseException] = {}
        self._hanging: set[uuid.UUID] = set()

    def fail_with(self, event_id: uuid.UUID, error: BaseException) -> None:
        self._failures[event_id] = error

    def hang_on(self, event_id: uuid.UUID) -> None:
        self._hanging.add(event_id)

    async def publish(self, message: OutboxMessage) -> None:
        if message.event_id in self._hanging:
            # The caller's asyncio.timeout is what should end this wait.
            await asyncio.sleep(HANG_GUARD_SECONDS)
            raise AssertionError("hang_on was not cut by the caller's timeout")
        if message.event_id in self._failures:
            raise self._failures[message.event_id]
        self.published.append(message)
