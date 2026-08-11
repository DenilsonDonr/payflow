from dataclasses import dataclass

from app.shared.messaging.in_process_event_bus import InProcessEventBus


@dataclass(frozen=True)
class _SubscribedEvent:
    payload: str


class TestInProcessEventBus:
    def test_subscribed_handler_receives_published_event_of_its_type(self):
        received: list[_SubscribedEvent] = []

        bus = InProcessEventBus()
        bus.subscribe(_SubscribedEvent, received.append)

        event = _SubscribedEvent(payload="ok")
        bus.publish(event)

        assert received == [event]
