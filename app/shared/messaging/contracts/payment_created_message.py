import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentCreatedMessage:
    payment_id: uuid.UUID
    amount: Decimal
    currency: str
