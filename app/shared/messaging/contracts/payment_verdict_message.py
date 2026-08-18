import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentVerdictMessage:
    payment_id: uuid.UUID
    verdict: str
