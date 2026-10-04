import logging

from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.domain.ports.event_publisher_port import EventPublisherPort

logger = logging.getLogger(__name__)


class LoggingEventPublisher(EventPublisherPort):
    """Stand-in until a real broker adapter (Kafka) exists: it only logs and never raises."""

    async def publish(self, message: OutboxMessage) -> None:
        logger.info(
            "published event_id=%s event_type=%s aggregate_type=%s aggregate_id=%s",
            message.event_id,
            message.event_type,
            message.aggregate_type,
            message.aggregate_id,
        )
