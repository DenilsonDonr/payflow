from abc import ABC, abstractmethod

from app.shared.outbox.domain.outbox_message import OutboxMessage


class EventPublisherPort(ABC):
    """Hands one message to a broker.

    Must raise on failure; returning normally means the broker accepted the
    message. Timeouts are enforced by the caller, not by the adapter.
    """

    @abstractmethod
    async def publish(self, message: OutboxMessage) -> None:
        pass
