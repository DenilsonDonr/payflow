import asyncio
import uuid

import pytest

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.tests.fakes import fake_event_publisher
from app.shared.outbox.tests.fakes.fake_event_publisher import FakeEventPublisher


def make_message() -> OutboxMessage:
    return OutboxMessage(
        id=1,
        event_id=uuid.uuid4(),
        aggregate_type="payment",
        aggregate_id=uuid.uuid4(),
        event_type="payment.created",
        payload="{}",
        attempts=0,
    )


class TestFakeEventPublisherHang:
    async def test_hang_is_cut_by_the_callers_timeout(self):
        publisher = FakeEventPublisher()
        message = make_message()
        publisher.hang_on(message.event_id)

        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.01):
                await publisher.publish(message)

        assert publisher.published == []

    async def test_hang_without_a_caller_timeout_fails_instead_of_hanging(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(fake_event_publisher, "HANG_GUARD_SECONDS", 0.01)
        publisher = FakeEventPublisher()
        message = make_message()
        publisher.hang_on(message.event_id)

        with pytest.raises(AssertionError, match="hang_on was not cut"):
            # The outer timeout only keeps this test itself from hanging if the guard breaks.
            async with asyncio.timeout(2):
                await publisher.publish(message)
