from dataclasses import dataclass

from app.shared.messaging.in_process_event_bus import InProcessEventBus


@dataclass(frozen=True)
class _SubscribedEvent:
    payload: str


@dataclass(frozen=True)
class _UnrelatedEvent:
    payload: str


class TestInProcessEventBus:
    def test_subscribed_handler_receives_published_event_of_its_type(self):
        received: list[_SubscribedEvent] = []

        bus = InProcessEventBus()
        bus.subscribe(_SubscribedEvent, received.append)

        event = _SubscribedEvent(payload="ok")
        bus.publish(event)

        assert received == [event]

    def test_published_unrelated_event_does_not_reach_subscribed_handler(self):
        received: list[_SubscribedEvent] = []

        bus = InProcessEventBus()
        bus.subscribe(_SubscribedEvent, received.append)

        bus.publish(_UnrelatedEvent(payload="ok"))

        assert received == []

    def test_multiple_subscribed_handlers_all_receive_published_event(self):
        received: list[_SubscribedEvent] = []
        received2: list[_SubscribedEvent] = []

        bus = InProcessEventBus()
        bus.subscribe(_SubscribedEvent, received.append)
        bus.subscribe(_SubscribedEvent, received2.append)

        event = _SubscribedEvent(payload="ok")
        bus.publish(event)

        assert received == [event]
        assert received2 == [event]

    def test_publish_with_no_subscribers_is_a_noop(self):
        bus = InProcessEventBus()

        event = _SubscribedEvent(payload="ok")
        bus.publish(event)
