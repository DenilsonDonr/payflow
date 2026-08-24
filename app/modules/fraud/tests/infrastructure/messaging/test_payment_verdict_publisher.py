import uuid

from app.modules.fraud.infrastructure.messaging.payment_verdict_publisher import (
    PaymentVerdictPublisher,
)
from app.shared.messaging.contracts.payment_verdict_message import PaymentVerdictMessage
from app.shared.messaging.in_process_event_bus import InProcessEventBus


class TestPaymentVerdictPublisher:
    def test_publishes_message_with_payment_verdict(self):
        payment_id = uuid.uuid4()

        received_messages: list[PaymentVerdictMessage] = []
        bus = InProcessEventBus()
        bus.subscribe(PaymentVerdictMessage, received_messages.append)

        publisher = PaymentVerdictPublisher(event_bus=bus)
        publisher.publish(payment_id=payment_id, verdict="approved")

        assert received_messages == [
            PaymentVerdictMessage(
                payment_id=payment_id,
                verdict="approved",
            )
        ]
