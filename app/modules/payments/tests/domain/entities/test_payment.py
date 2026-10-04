import uuid
from decimal import Decimal

import pytest

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.events.payment_created import PaymentCreated
from app.modules.payments.domain.exceptions.invalid_payment_transition import (
    InvalidPaymentTransitionError,
)
from app.modules.payments.domain.value_objects.money import Money

DEFAULT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
EVENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000e1")


def money(amount: str = "100.00", currency: str = "USD") -> Money:
    return Money(amount=Decimal(amount), currency=currency)


def make_payment(id: uuid.UUID = DEFAULT_ID, amount: Money | None = None) -> Payment:
    return Payment(id=id, user_id=USER_ID, amount=amount if amount is not None else money())


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
    def test_creates_payment_with_given_id_user_and_amount(self):
        payment = Payment(id=DEFAULT_ID, user_id=USER_ID, amount=money())

        assert payment.id == DEFAULT_ID
        assert payment.user_id == USER_ID
        assert payment.amount == money()

    def test_is_always_born_pending(self):
        assert make_payment().state == PaymentState.PENDING

    @pytest.mark.parametrize(
        "id", [None, 123, 1.5, True, [], "11111111-1111-1111-1111-111111111111"]
    )
    def test_rejects_non_uuid_id(self, id: object):
        with pytest.raises(TypeError, match="Payment ID must be a UUID"):
            Payment(id=id, user_id=USER_ID, amount=money())  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("amount", [None, 100.00, "100.00", True, Decimal("100.00"), 100])
    def test_rejects_non_money_amount(self, amount: object):
        with pytest.raises(TypeError, match="Payment amount must be an instance of Money"):
            Payment(id=DEFAULT_ID, user_id=USER_ID, amount=amount)  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize(
        "user_id", [None, 123, 1.5, True, [], "11111111-1111-1111-1111-111111111111"]
    )
    def test_rejects_non_uuid_user_id(self, user_id: object):
        with pytest.raises(TypeError, match="Payment user ID must be a UUID"):
            Payment(id=DEFAULT_ID, user_id=user_id, amount=money())  # pyright: ignore[reportArgumentType]


class TestPaymentTransitions:
    @pytest.mark.parametrize(
        ("from_state", "action", "expected_state"),
        [
            pytest.param(
                PaymentState.PENDING, "approve", PaymentState.APPROVED, id="pending->approved"
            ),
            pytest.param(
                PaymentState.PENDING, "reject", PaymentState.REJECTED, id="pending->rejected"
            ),
            pytest.param(
                PaymentState.APPROVED, "complete", PaymentState.COMPLETED, id="approved->completed"
            ),
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
        [
            pytest.param(state, action, id=f"{state.value}-cannot-{action}")
            for state, action in ILLEGAL_TRANSITIONS
        ],
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

    def test_reconstitute_restores_the_given_state(self):
        payment = Payment.reconstitute(DEFAULT_ID, USER_ID, money(), PaymentState.APPROVED)

        assert payment.state == PaymentState.APPROVED

    def test_reconstitute_restores_the_given_user(self):
        payment = Payment.reconstitute(DEFAULT_ID, USER_ID, money(), PaymentState.APPROVED)

        assert payment.user_id == USER_ID


class TestPaymentImmutability:
    @pytest.mark.parametrize(
        ("attribute", "value"),
        [
            ("id", OTHER_ID),
            ("user_id", OTHER_ID),
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


def created_event_stub() -> PaymentCreated:
    return PaymentCreated(
        event_id=EVENT_ID,
        payment_id=DEFAULT_ID,
        user_id=USER_ID,
        amount=money(),
        state="pending",
    )


class TestPaymentEvents:
    def test_create_records_exactly_one_payment_created_event(self):
        payment = Payment.create(id=DEFAULT_ID, user_id=USER_ID, amount=money(), event_id=EVENT_ID)

        events = payment.pull_events()

        assert len(events) == 1
        assert isinstance(events[0], PaymentCreated)

    def test_create_event_carries_the_injected_event_id_and_the_payment_id(self):
        payment = Payment.create(id=DEFAULT_ID, user_id=USER_ID, amount=money(), event_id=EVENT_ID)

        (event,) = payment.pull_events()

        assert event.event_id == EVENT_ID
        assert event.aggregate_id == DEFAULT_ID

    def test_create_builds_a_pending_payment_with_the_given_data(self):
        amount = money("42.00", "EUR")

        payment = Payment.create(id=DEFAULT_ID, user_id=USER_ID, amount=amount, event_id=EVENT_ID)

        assert payment.id == DEFAULT_ID
        assert payment.user_id == USER_ID
        assert payment.amount == amount
        assert payment.state is PaymentState.PENDING

    def test_event_payload_describes_the_created_payment(self):
        payment = Payment.create(
            id=DEFAULT_ID, user_id=USER_ID, amount=money("100.00"), event_id=EVENT_ID
        )

        (event,) = payment.pull_events()

        assert event.payload() == {
            "id": str(DEFAULT_ID),
            "user_id": str(USER_ID),
            "amount": "100.00",
            "currency": "USD",
            "state": "pending",
        }

    def test_pull_events_drains_the_accumulated_events(self):
        payment = Payment.create(id=DEFAULT_ID, user_id=USER_ID, amount=money(), event_id=EVENT_ID)

        first = payment.pull_events()
        second = payment.pull_events()

        assert len(first) == 1
        assert second == []

    def test_mutating_the_pulled_list_does_not_affect_the_payment(self):
        payment = Payment.create(id=DEFAULT_ID, user_id=USER_ID, amount=money(), event_id=EVENT_ID)

        # Mutating a pulled list must never leak back into the entity's own state.
        payment.pull_events().append(created_event_stub())

        assert payment.pull_events() == []

    def test_a_payment_built_with_init_records_no_event(self):
        assert make_payment().pull_events() == []

    def test_a_reconstituted_payment_records_no_event(self):
        payment = Payment.reconstitute(DEFAULT_ID, USER_ID, money(), PaymentState.APPROVED)

        assert payment.pull_events() == []

    def test_transitions_do_not_record_events_yet(self):
        payment = payment_in(PaymentState.COMPLETED)

        assert payment.pull_events() == []
