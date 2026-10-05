import logging

import pytest

from app.shared.outbox.infrastructure import relay_worker
from app.shared.outbox.infrastructure.relay_worker import warn_about_stand_in_publisher


class TestStandInPublisherWarning:
    def test_warns_that_the_logging_publisher_delivers_nowhere(
        self, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.INFO, logger=relay_worker.__name__):
            warn_about_stand_in_publisher()

        records = [r for r in caplog.records if r.name == relay_worker.__name__]
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING
        text = records[0].getMessage()
        assert "LoggingEventPublisher" in text
        assert "nowhere" in text
