import uuid
from dataclasses import dataclass

from app.modules.payments.domain.events.domain_event import DomainEvent
from app.modules.payments.domain.value_objects.money import Money


@dataclass(frozen=True)
class PaymentCreated(DomainEvent):
    event_id: uuid.UUID
    payment_id: uuid.UUID
    user_id: uuid.UUID
    amount: Money
    state: str

    @property
    def aggregate_type(self) -> str:
        return "payment"

    @property
    def aggregate_id(self) -> uuid.UUID:
        return self.payment_id

    @property
    def event_type(self) -> str:
        return "payment.created"

    def payload(self) -> dict[str, object]:
        return {
            "id": str(self.payment_id),
            "user_id": str(self.user_id),
            # Decimal as str: a float would silently lose precision on money.
            "amount": str(self.amount.amount),
            "currency": self.amount.currency,
            "state": self.state,
        }
