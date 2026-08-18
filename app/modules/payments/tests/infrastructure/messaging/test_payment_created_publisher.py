import uuid
from decimal import Decimal

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.infrastructure.messaging.payment_created_message import (
    PaymentCreatedMessage,
)
from app.modules.payments.infrastructure.messaging.payment_created_publisher import (
    PaymentCreatedPublisher,
)
from app.shared.messaging.in_process_event_bus import InProcessEventBus


class TestPaymentCreatedPublisher:
    def test_publishes_message_with_payment_data(self):
        payment = Payment(id=uuid.uuid4(), amount=Money(Decimal("100.00"), "USD"))

        received_messages: list[PaymentCreatedMessage] = []
        bus = InProcessEventBus()
        bus.subscribe(PaymentCreatedMessage, received_messages.append)

        publisher = PaymentCreatedPublisher(event_bus=bus)
        publisher.publish(payment)

        assert received_messages == [
            PaymentCreatedMessage(
                payment_id=payment.id,
                amount=Decimal("100.00"),
                currency="USD",
            )
        ]
