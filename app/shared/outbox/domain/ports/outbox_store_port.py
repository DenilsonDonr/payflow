from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from app.shared.outbox.domain.outbox_message import OutboxMessage


class ClaimedOutboxBatch(ABC):
    """Rows locked by one `claim`, plus the outcomes the relay records for them."""

    @property
    @abstractmethod
    def messages(self) -> list[OutboxMessage]:
        pass

    @abstractmethod
    async def mark_published(self, message_id: int) -> None:
        pass

    @abstractmethod
    async def reschedule(self, message_id: int, *, delay_seconds: float, error: str) -> None:
        """Record a failed attempt and retry later.

        Increments the row's `attempts` by one, and the row becomes claimable
        again only after `delay_seconds`. The relay's retry ceiling
        (`attempts + 1 >= max_attempts`) terminates only if every adapter
        honours this increment.
        """

    @abstractmethod
    async def mark_failed(self, message_id: int, *, error: str) -> None:
        """Record the final failed attempt; the row is never claimed again.

        Increments the row's `attempts` by one, like `reschedule`, so the
        stored count always equals the publish attempts actually made.
        """


class OutboxStorePort(ABC):
    @abstractmethod
    def claim(self, limit: int) -> AbstractAsyncContextManager[ClaimedOutboxBatch]:
        """Claim up to `limit` due pending rows, oldest `available_at` first.

        The `async with` block is ONE transaction. The claimed rows stay locked
        for its duration and are invisible to other claimers (SKIP LOCKED in
        the Postgres adapter). Leaving the block normally commits every outcome
        recorded on the batch; leaving it by an exception rolls everything back
        and the rows stay pending and unchanged.
        """
