import uuid
from enum import Enum

from app.modules.payments.domain.value_objects.money import Money

class PaymentState(Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'

class Payment:
    def __init__(self, id: uuid.UUID, amount: Money):
        # Type hints are not enforced at runtime, so callers can pass any type.
        if not isinstance(id, uuid.UUID): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Payment ID must be a UUID.")
        if not isinstance(amount, Money): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Payment amount must be an instance of Money.")

        self._id = id
        self._state = PaymentState.PENDING
        self._amount = amount
        
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Payment):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
    
    def __repr__(self) -> str:
        return f"Payment(id={self._id!r}, amount={self._amount!r}, state={self._state!r})"
        
    @property
    def id(self) -> uuid.UUID:
        return self._id
    
    @property
    def state(self) -> PaymentState:
        return self._state
    
    @property
    def amount(self) -> Money:
        return self._amount
    
    def complete(self) -> None:
        if self._state != PaymentState.PENDING:
            raise ValueError("Only pending payments can be completed.")
        
        self._state = PaymentState.COMPLETED
    
    def fail(self) -> None:
        if self._state != PaymentState.PENDING:
            raise ValueError("Only pending payments can be failed.")
        
        self._state = PaymentState.FAILED
        
