import uuid

from app.shared.messaging.contracts.payment_verdict_message import PaymentVerdictMessage
from app.shared.messaging.event_bus import EventBus


class PaymentVerdictPublisher:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def publish(self, payment_id: uuid.UUID, verdict: str) -> None:
        message = PaymentVerdictMessage(payment_id=payment_id, verdict=verdict)
        self.event_bus.publish(message)
