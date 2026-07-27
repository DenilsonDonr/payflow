from collections.abc import Callable
from decimal import Decimal

import pytest

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.value_objects.money import Money

DEFAULT_ID = "UUID-0001"

def money(amount: str = "100.00", currency: str = "USD") -> Money:
    return Money(amount=Decimal(amount), currency=currency)

def make_payment(id: str = DEFAULT_ID, amount: Money | None = None) -> Payment:
    return Payment(id=id, amount=amount if amount is not None else money())

class TestPaymentCreation:
    def test_creates_payment_with_given_id_and_amount(self):
        payment = Payment(id=DEFAULT_ID, amount=money())

        assert payment.id == DEFAULT_ID
        assert payment.amount == money()

    def test_is_always_born_pending(self):
        assert make_payment().state == PaymentState.PENDING

    @pytest.mark.parametrize("id", [None, 123, 1.5, True, [], ("UUID-0001",)])
    def test_rejects_non_string_id(self, id: object):
        with pytest.raises(TypeError, match="Payment ID must be a string"):
            Payment(id=id, amount=money())  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("id", ["", " ", "   ", "\n", "\t"])
    def test_rejects_blank_id(self, id: str):
        with pytest.raises(ValueError, match="Payment ID cannot be empty"):
            Payment(id=id, amount=money())

    @pytest.mark.parametrize("amount", [None, 100.00, "100.00", True, Decimal("100.00"), 100])
    def test_rejects_non_money_amount(self, amount: object):
        with pytest.raises(TypeError, match="Payment amount must be an instance of Money"):
            Payment(id=DEFAULT_ID, amount=amount)  # pyright: ignore[reportArgumentType]

    def test_strips_surrounding_whitespace_from_id(self):
        assert Payment(id=f"  {DEFAULT_ID}  ", amount=money()).id == DEFAULT_ID


class TestPaymentTransitions:
    def test_pending_payment_can_be_completed(self):
        payment = make_payment()

        payment.complete()

        assert payment.state == PaymentState.COMPLETED

    def test_pending_payment_can_be_failed(self):
        payment = make_payment()

        payment.fail()

        assert payment.state == PaymentState.FAILED

    @pytest.mark.parametrize(
        ("reach_terminal", "attempted_action", "expected_state", "expected_message"),
        [
            pytest.param(
                Payment.complete,
                Payment.complete,
                PaymentState.COMPLETED,
                "Only pending payments can be completed",
                id="completed-cannot-be-completed",
            ),
            pytest.param(
                Payment.complete,
                Payment.fail,
                PaymentState.COMPLETED,
                "Only pending payments can be failed",
                id="completed-cannot-be-failed",
            ),
            pytest.param(
                Payment.fail,
                Payment.fail,
                PaymentState.FAILED,
                "Only pending payments can be failed",
                id="failed-cannot-be-failed",
            ),
            pytest.param(
                Payment.fail,
                Payment.complete,
                PaymentState.FAILED,
                "Only pending payments can be completed",
                id="failed-cannot-be-completed",
            ),
        ],
    )
    def test_rejects_transitions_out_of_a_terminal_state(
        self,
        reach_terminal: Callable[[Payment], None],
        attempted_action: Callable[[Payment], None],
        expected_state: PaymentState,
        expected_message: str,
    ):
        payment = make_payment()
        reach_terminal(payment)

        with pytest.raises(ValueError, match=expected_message):
            attempted_action(payment)

        assert payment.state == expected_state

    @pytest.mark.parametrize("action", [Payment.complete, Payment.fail])
    def test_transition_does_not_change_id_or_amount(
        self, action: Callable[[Payment], None]
    ):
        payment = make_payment(amount=money("250.50"))

        action(payment)

        assert payment.id == DEFAULT_ID
        assert payment.amount == money("250.50")


class TestPaymentImmutability:
    @pytest.mark.parametrize(
        ("attribute", "value"),
        [
            ("id", "UUID-0002"),
            ("state", PaymentState.PENDING),
            ("amount", money("999.99")),
        ],
    )
    def test_attributes_cannot_be_reassigned(self, attribute: str, value: object):
        payment = make_payment()

        with pytest.raises(AttributeError):
            setattr(payment, attribute, value)

    def test_a_terminal_payment_cannot_be_revived_through_the_state_attribute(self):
        payment = make_payment()
        payment.complete()

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
        completed = make_payment()
        completed.complete()

        assert pending == completed

    def test_different_id_is_a_different_payment(self):
        assert make_payment(id="UUID-0001") != make_payment(id="UUID-0002")

    def test_id_whitespace_does_not_create_a_second_payment(self):
        assert make_payment(id=DEFAULT_ID) == make_payment(id=f"  {DEFAULT_ID}  ")

    @pytest.mark.parametrize("other", [None, DEFAULT_ID, 123, object(), money()])
    def test_is_not_equal_to_a_non_payment(self, other: object):
        assert make_payment() != other

    def test_same_id_produces_the_same_hash(self):
        assert hash(make_payment(amount=money("100.00"))) == hash(
            make_payment(amount=money("200.00"))
        )

    def test_payments_with_the_same_id_collapse_into_one_set_entry(self):
        assert len({make_payment(), make_payment(), make_payment(id="UUID-0002")}) == 2


class TestPaymentRepresentation:
    def test_repr_shows_id_and_state(self):
        payment = make_payment()

        assert DEFAULT_ID in repr(payment)
        assert "PENDING" in repr(payment).upper()
