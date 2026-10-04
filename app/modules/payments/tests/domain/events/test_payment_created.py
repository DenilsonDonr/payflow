import uuid
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.modules.payments.domain.events.domain_event import DomainEvent
from app.modules.payments.domain.events.payment_created import PaymentCreated
from app.modules.payments.domain.value_objects.money import Money

EVENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000e1")
PAYMENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def make_event() -> PaymentCreated:
    return PaymentCreated(
        event_id=EVENT_ID,
        payment_id=PAYMENT_ID,
        user_id=USER_ID,
        amount=Money(amount=Decimal("100.50"), currency="usd"),
        state="pending",
    )


class TestPaymentCreatedIdentity:
    def test_is_a_domain_event(self):
        assert isinstance(make_event(), DomainEvent)

    def test_exposes_the_injected_event_id(self):
        assert make_event().event_id == EVENT_ID

    def test_aggregate_type_is_payment(self):
        assert make_event().aggregate_type == "payment"

    def test_event_type_is_payment_created(self):
        assert make_event().event_type == "payment.created"

    def test_aggregate_id_is_the_payment_id(self):
        assert make_event().aggregate_id == PAYMENT_ID


class TestPaymentCreatedPayload:
    def test_payload_is_json_safe_with_the_exact_expected_values(self):
        assert make_event().payload() == {
            "id": "00000000-0000-0000-0000-000000000001",
            "user_id": "00000000-0000-0000-0000-0000000000aa",
            "amount": "100.50",
            "currency": "USD",
            "state": "pending",
        }

    def test_amount_is_a_string_never_a_float(self):
        assert isinstance(make_event().payload()["amount"], str)

    def test_amount_keeps_decimal_precision_that_a_float_would_lose(self):
        event = PaymentCreated(
            event_id=EVENT_ID,
            payment_id=PAYMENT_ID,
            user_id=USER_ID,
            amount=Money(amount=Decimal("0.10000000000000000555"), currency="USD"),
            state="pending",
        )

        assert event.payload()["amount"] == "0.10000000000000000555"


class TestPaymentCreatedImmutability:
    def test_cannot_be_modified(self):
        event = make_event()

        with pytest.raises(FrozenInstanceError):
            event.event_id = uuid.uuid4()  # pyright: ignore[reportAttributeAccessIssue]
