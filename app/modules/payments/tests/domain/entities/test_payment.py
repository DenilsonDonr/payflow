import uuid
from decimal import Decimal

import pytest

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.exceptions.invalid_payment_transition import (InvalidPaymentTransitionError)
from app.modules.payments.domain.value_objects.money import Money

DEFAULT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

def money(amount: str = "100.00", currency: str = "USD") -> Money:
    return Money(amount=Decimal(amount), currency=currency)

def make_payment(id: uuid.UUID = DEFAULT_ID, amount: Money | None = None) -> Payment:
    return Payment(id=id, amount=amount if amount is not None else money())

def payment_in(state: PaymentState, amount: Money | None = None) -> Payment:
    """Drive a fresh payment into `state` through its legal transitions only."""
    payment = make_payment(amount=amount)
    if state is PaymentState.PENDING:
        return payment
    if state is PaymentState.APPROVED:
        payment.approve()
        return payment
    if state is PaymentState.REJECTED:
        payment.reject()
        return payment
    if state is PaymentState.COMPLETED:
        payment.approve()
        payment.complete()
        return payment
    if state is PaymentState.FAILED:
        payment.approve()
        payment.fail()
        return payment
    raise AssertionError(f"unhandled state: {state}")

ACTIONS = ("approve", "reject", "complete", "fail")

LEGAL_TRANSITIONS = {
    (PaymentState.PENDING, "approve"),
    (PaymentState.PENDING, "reject"),
    (PaymentState.APPROVED, "complete"),
    (PaymentState.APPROVED, "fail"),
}

ILLEGAL_TRANSITIONS = [
    (state, action)
    for state in PaymentState
    for action in ACTIONS
    if (state, action) not in LEGAL_TRANSITIONS
]

class TestPaymentCreation:
    def test_creates_payment_with_given_id_and_amount(self):
        payment = Payment(id=DEFAULT_ID, amount=money())

        assert payment.id == DEFAULT_ID
        assert payment.amount == money()

    def test_is_always_born_pending(self):
        assert make_payment().state == PaymentState.PENDING

    @pytest.mark.parametrize("id", [None, 123, 1.5, True, [], "11111111-1111-1111-1111-111111111111"])
    def test_rejects_non_uuid_id(self, id: object):
        with pytest.raises(TypeError, match="Payment ID must be a UUID"):
            Payment(id=id, amount=money())  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("amount", [None, 100.00, "100.00", True, Decimal("100.00"), 100])
    def test_rejects_non_money_amount(self, amount: object):
        with pytest.raises(TypeError, match="Payment amount must be an instance of Money"):
            Payment(id=DEFAULT_ID, amount=amount)  # pyright: ignore[reportArgumentType]


class TestPaymentTransitions:
    @pytest.mark.parametrize(
        ("from_state", "action", "expected_state"),
        [
            pytest.param(PaymentState.PENDING, "approve", PaymentState.APPROVED, id="pending->approved"),
            pytest.param(PaymentState.PENDING, "reject", PaymentState.REJECTED, id="pending->rejected"),
            pytest.param(PaymentState.APPROVED, "complete", PaymentState.COMPLETED, id="approved->completed"),
            pytest.param(PaymentState.APPROVED, "fail", PaymentState.FAILED, id="approved->failed"),
        ],
    )
    def test_allows_legal_transitions(
        self, from_state: PaymentState, action: str, expected_state: PaymentState
    ):
        payment = payment_in(from_state)

        getattr(payment, action)()

        assert payment.state == expected_state

    @pytest.mark.parametrize(
        ("from_state", "action"),
        [pytest.param(state, action, id=f"{state.value}-cannot-{action}") for state, action in ILLEGAL_TRANSITIONS],
    )
    def test_rejects_illegal_transitions(self, from_state: PaymentState, action: str):
        payment = payment_in(from_state)

        with pytest.raises(InvalidPaymentTransitionError):
            getattr(payment, action)()

        assert payment.state == from_state

    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_transition_does_not_change_id_or_amount(self, action: str):
        payment = make_payment(amount=money("250.50"))

        getattr(payment, action)()

        assert payment.id == DEFAULT_ID
        assert payment.amount == money("250.50")


class TestPaymentImmutability:
    @pytest.mark.parametrize(
        ("attribute", "value"),
        [
            ("id", OTHER_ID),
            ("state", PaymentState.PENDING),
            ("amount", money("999.99")),
        ],
    )
    def test_attributes_cannot_be_reassigned(self, attribute: str, value: object):
        payment = make_payment()

        with pytest.raises(AttributeError):
            setattr(payment, attribute, value)

    def test_a_terminal_payment_cannot_be_revived_through_the_state_attribute(self):
        payment = payment_in(PaymentState.COMPLETED)

        with pytest.raises(AttributeError):
            payment.state = PaymentState.PENDING  # pyright: ignore[reportAttributeAccessIssue]

        assert payment.state == PaymentState.COMPLETED


class TestPaymentIdentity:
    def test_is_equal_to_itself(self):
        payment = make_payment()

        assert payment == payment

    def test_same_id_is_the_same_payment_even_with_different_amount(self):
        assert make_payment(amount=money("100.00")) == make_payment(amount=money("200.00"))

    def test_same_id_is_the_same_payment_even_in_a_different_state(self):
        pending = make_payment()
        approved = payment_in(PaymentState.APPROVED)

        assert pending == approved

    def test_different_id_is_a_different_payment(self):
        assert make_payment(id=DEFAULT_ID) != make_payment(id=OTHER_ID)

    @pytest.mark.parametrize("other", [None, DEFAULT_ID, 123, object(), money()])
    def test_is_not_equal_to_a_non_payment(self, other: object):
        assert make_payment() != other

    def test_same_id_produces_the_same_hash(self):
        assert hash(make_payment(amount=money("100.00"))) == hash(
            make_payment(amount=money("200.00"))
        )

    def test_payments_with_the_same_id_collapse_into_one_set_entry(self):
        assert len({make_payment(), make_payment(), make_payment(id=OTHER_ID)}) == 2


class TestPaymentRepresentation:
    def test_repr_shows_id_and_state(self):
        payment = make_payment()

        assert str(DEFAULT_ID) in repr(payment)
        assert "PENDING" in repr(payment).upper()
