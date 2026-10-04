import uuid
from enum import Enum

from app.modules.payments.domain.events.domain_event import DomainEvent
from app.modules.payments.domain.events.payment_created import PaymentCreated
from app.modules.payments.domain.exceptions.invalid_payment_transition import (
    InvalidPaymentTransitionError,
)
from app.modules.payments.domain.value_objects.money import Money


class PaymentState(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class Payment:
    def __init__(self, id: uuid.UUID, user_id: uuid.UUID, amount: Money):
        # Type hints are not enforced at runtime, so callers can pass any type.
        if not isinstance(id, uuid.UUID):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Payment ID must be a UUID.")
        # Only the identifier: the payments module never depends on the auth module's User.
        if not isinstance(user_id, uuid.UUID):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Payment user ID must be a UUID.")
        if not isinstance(amount, Money):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Payment amount must be an instance of Money.")

        self._id = id
        self._user_id = user_id
        self._state = PaymentState.PENDING
        self._amount = amount
        self._events: list[DomainEvent] = []

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
    def user_id(self) -> uuid.UUID:
        return self._user_id

    @property
    def state(self) -> PaymentState:
        return self._state

    @property
    def amount(self) -> Money:
        return self._amount

    def pull_events(self) -> list[DomainEvent]:
        """Return the accumulated events and clear them, so each is published once."""
        events = self._events
        self._events = []
        return events

    def approve(self) -> None:
        self._transition(to_state=PaymentState.APPROVED, allowed_from=PaymentState.PENDING)

    def reject(self) -> None:
        self._transition(to_state=PaymentState.REJECTED, allowed_from=PaymentState.PENDING)

    def complete(self) -> None:
        self._transition(to_state=PaymentState.COMPLETED, allowed_from=PaymentState.APPROVED)

    def fail(self) -> None:
        self._transition(to_state=PaymentState.FAILED, allowed_from=PaymentState.APPROVED)

    def _transition(self, to_state: PaymentState, allowed_from: PaymentState) -> None:
        if self._state is not allowed_from:
            raise InvalidPaymentTransitionError(
                f"Cannot move a payment from {self._state.value} to {to_state.value}."
            )
        self._state = to_state

    @classmethod
    def create(
        cls, id: uuid.UUID, user_id: uuid.UUID, amount: Money, event_id: uuid.UUID
    ) -> "Payment":
        payment = cls(id=id, user_id=user_id, amount=amount)
        payment._events.append(
            PaymentCreated(
                event_id=event_id,
                payment_id=payment.id,
                user_id=payment.user_id,
                amount=payment.amount,
                state=payment.state.value,
            )
        )
        return payment

    @classmethod
    def reconstitute(
        cls, id: uuid.UUID, user_id: uuid.UUID, amount: Money, state: PaymentState
    ) -> "Payment":
        payment = cls(id=id, user_id=user_id, amount=amount)
        payment._state = state
        return payment
