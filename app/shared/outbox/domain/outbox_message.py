import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class OutboxMessage:
    """Transport view of an outbox row, as the relay hands it to a publisher.

    Not a domain event: it knows nothing about payments, only about delivery.
    `attempts` is the number of failed attempts recorded before this one.
    `payload` is the serialized JSON body, never parsed by the relay.
    """

    id: int
    event_id: uuid.UUID
    aggregate_type: str
    aggregate_id: uuid.UUID
    event_type: str
    payload: str
    attempts: int
