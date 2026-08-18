from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.infrastructure.messaging.payment_created_message import (
    PaymentCreatedMessage,
)
from app.shared.messaging.event_bus import EventBus


class PaymentCreatedPublisher:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def publish(self, payment: Payment) -> None:
        message = PaymentCreatedMessage(
            payment_id=payment.id,
            amount=payment.amount.amount,
            currency=payment.amount.currency,
        )
        self.event_bus.publish(message)
