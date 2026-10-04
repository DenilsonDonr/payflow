import logging
import uuid

import pytest

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.infrastructure.publishing.logging_event_publisher import (
    LoggingEventPublisher,
)


def make_message() -> OutboxMessage:
    return OutboxMessage(
        id=1,
        event_id=uuid.uuid4(),
        aggregate_type="payment",
        aggregate_id=uuid.uuid4(),
        event_type="payment.created",
        payload='{"amount": "10.00"}',
        attempts=0,
    )


class TestLoggingEventPublisher:
    async def test_logs_one_info_record_per_message(self, caplog: pytest.LogCaptureFixture):
        message = make_message()

        with caplog.at_level(logging.INFO):
            await LoggingEventPublisher().publish(message)

        records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(records) == 1

    async def test_record_identifies_the_event(self, caplog: pytest.LogCaptureFixture):
        message = make_message()

        with caplog.at_level(logging.INFO):
            await LoggingEventPublisher().publish(message)

        text = caplog.records[0].getMessage()
        assert str(message.event_id) in text
        assert message.event_type in text
        assert message.aggregate_type in text
        assert str(message.aggregate_id) in text

    async def test_returns_none(self):
        result = await LoggingEventPublisher().publish(make_message())

        assert result is None
