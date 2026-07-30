import uuid
from decimal import Decimal

from pydantic import BaseModel

class PaymentCreateRequest(BaseModel):
    amount: Decimal
    currency: str

class PaymentResponse(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: str
    state: str
