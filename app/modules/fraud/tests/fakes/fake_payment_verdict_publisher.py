import uuid

from app.modules.fraud.infrastructure.messaging.payment_verdict_publisher import (
    PaymentVerdictPublisher,
)


class FakePaymentVerdictPublisher(PaymentVerdictPublisher):
    def __init__(self) -> None:
        self.payment_id_called_with: uuid.UUID | None = None
        self.verdict_called_with: str | None = None

    def publish(self, payment_id: uuid.UUID, verdict: str) -> None:
        self.payment_id_called_with = payment_id
        self.verdict_called_with = verdict
