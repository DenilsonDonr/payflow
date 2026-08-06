import uuid
from decimal import Decimal

from pydantic import BaseModel, field_validator


class PaymentCreateRequest(BaseModel):
    amount: Decimal
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a 3-letter ISO 4217 code.")
        return value

class PaymentResponse(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: str
    state: str
