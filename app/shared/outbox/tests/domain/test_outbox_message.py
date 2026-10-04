import dataclasses
import typing
import uuid

import pytest

from app.shared.outbox.domain.outbox_message import OutboxMessage


def make_message(**overrides: typing.Any) -> OutboxMessage:
    fields: dict[str, typing.Any] = {
        "id": 1,
        "event_id": uuid.uuid4(),
        "aggregate_type": "payment",
        "aggregate_id": uuid.uuid4(),
        "event_type": "payment.created",
        "payload": '{"amount": "10.00"}',
        "attempts": 0,
    }
    fields.update(overrides)
    return OutboxMessage(**fields)


class TestOutboxMessage:
    def test_is_immutable(self):
        message = make_message(payload="{}")

        with pytest.raises(dataclasses.FrozenInstanceError):
            message.attempts = 1  # type: ignore[misc]

    def test_payload_is_declared_as_json_text(self):
        hints = typing.get_type_hints(OutboxMessage)

        assert hints["payload"] is str

    def test_equal_messages_are_hashable_and_hash_equal(self):
        event_id = uuid.uuid4()
        aggregate_id = uuid.uuid4()
        first = make_message(event_id=event_id, aggregate_id=aggregate_id)
        second = make_message(event_id=event_id, aggregate_id=aggregate_id)

        assert first == second
        assert hash(first) == hash(second)
        assert len({first, second}) == 1
