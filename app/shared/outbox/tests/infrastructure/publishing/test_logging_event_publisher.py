import logging
import uuid
from dataclasses import replace

import pytest

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.infrastructure.publishing import logging_event_publisher
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


def publisher_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.name == logging_event_publisher.__name__ and r.levelno == logging.INFO
    ]


class TestLoggingEventPublisher:
    async def test_logs_one_info_record_per_message(self, caplog: pytest.LogCaptureFixture):
        message = make_message()

        with caplog.at_level(logging.INFO):
            await LoggingEventPublisher().publish(message)

        assert len(publisher_records(caplog)) == 1

    async def test_record_identifies_the_event(self, caplog: pytest.LogCaptureFixture):
        message = make_message()

        with caplog.at_level(logging.INFO):
            await LoggingEventPublisher().publish(message)

        text = publisher_records(caplog)[0].getMessage()
        assert str(message.event_id) in text
        assert message.event_type in text
        assert message.aggregate_type in text
        assert str(message.aggregate_id) in text

    async def test_record_includes_the_outbox_row_id(self, caplog: pytest.LogCaptureFixture):
        message = replace(make_message(), id=4242)

        with caplog.at_level(logging.INFO):
            await LoggingEventPublisher().publish(message)

        assert "outbox_id=4242" in publisher_records(caplog)[0].getMessage()

    async def test_returns_none(self):
        result = await LoggingEventPublisher().publish(make_message())

        assert result is None
