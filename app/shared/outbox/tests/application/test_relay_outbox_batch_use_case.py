import asyncio
import math
import uuid

import pytest

from app.shared.outbox.application.relay_outbox_batch_use_case import RelayOutboxBatchUseCase
from app.shared.outbox.domain.outbox_message import OutboxMessage
from app.shared.outbox.tests.fakes.fake_event_publisher import FakeEventPublisher
from app.shared.outbox.tests.fakes.in_memory_outbox_store import InMemoryOutboxStore

FIXED_DELAY = 12.5
TIMEOUT_SECONDS = 0.01


def make_message(message_id: int, attempts: int = 0) -> OutboxMessage:
    return OutboxMessage(
        id=message_id,
        event_id=uuid.uuid4(),
        aggregate_type="payment",
        aggregate_id=uuid.uuid4(),
        event_type="payment.created",
        payload="{}",
        attempts=attempts,
    )


class StubBackoff:
    """Records the `attempts` it was called with and always returns the same delay."""

    def __init__(self, delay: float = FIXED_DELAY) -> None:
        self._delay = delay
        self.calls: list[int] = []

    def __call__(self, attempts: int) -> float:
        self.calls.append(attempts)
        return self._delay


def build_use_case(
    store: InMemoryOutboxStore,
    publisher: FakeEventPublisher,
    backoff: StubBackoff | None = None,
    *,
    batch_size: int = 10,
    max_attempts: int = 5,
    publish_timeout_seconds: float = 1.0,
) -> RelayOutboxBatchUseCase:
    return RelayOutboxBatchUseCase(
        store,
        publisher,
        batch_size=batch_size,
        max_attempts=max_attempts,
        publish_timeout_seconds=publish_timeout_seconds,
        backoff=backoff or StubBackoff(),
    )


class TestRelayOutboxBatchUseCaseSuccess:
    async def test_publishes_marks_published_and_returns_the_claimed_count(self):
        messages = [make_message(1), make_message(2)]
        store = InMemoryOutboxStore(messages)
        publisher = FakeEventPublisher()

        claimed = await build_use_case(store, publisher).execute()

        assert claimed == 2
        assert publisher.published == messages
        assert store.published == [1, 2]
        assert store.rescheduled == {}
        assert store.failed == {}
        assert store.commits == 1

    async def test_empty_store_returns_zero_and_records_nothing(self):
        store = InMemoryOutboxStore([])
        publisher = FakeEventPublisher()

        claimed = await build_use_case(store, publisher).execute()

        assert claimed == 0
        assert publisher.published == []
        assert store.published == []
        assert store.rescheduled == {}
        assert store.failed == {}

    async def test_claims_no_more_than_batch_size(self):
        store = InMemoryOutboxStore([make_message(i) for i in range(1, 6)])
        publisher = FakeEventPublisher()

        claimed = await build_use_case(store, publisher, batch_size=2).execute()

        assert claimed == 2
        assert store.published == [1, 2]
        assert [m.id for m in publisher.published] == [1, 2]


class TestRelayOutboxBatchUseCasePublishFailure:
    async def test_reschedules_with_the_backoff_delay_for_the_previous_attempts(self):
        message = make_message(1, attempts=2)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, ConnectionError("broker down"))
        backoff = StubBackoff()

        claimed = await build_use_case(store, publisher, backoff).execute()

        assert claimed == 1
        assert backoff.calls == [2]
        assert store.rescheduled == {1: (FIXED_DELAY, "ConnectionError: broker down")}
        assert store.published == []
        assert store.failed == {}

    async def test_timeout_is_treated_as_a_failure_and_rescheduled(self):
        message = make_message(1)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.hang_on(message.event_id)

        await build_use_case(store, publisher, publish_timeout_seconds=TIMEOUT_SECONDS).execute()

        delay, error = store.rescheduled[1]
        assert delay == FIXED_DELAY
        assert error.startswith("TimeoutError")
        assert store.published == []

    async def test_reaching_max_attempts_marks_failed_without_rescheduling(self):
        message = make_message(1, attempts=4)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, RuntimeError("still down"))
        backoff = StubBackoff()

        await build_use_case(store, publisher, backoff, max_attempts=5).execute()

        assert store.failed == {1: "RuntimeError: still down"}
        assert store.rescheduled == {}
        assert backoff.calls == []

    async def test_one_attempt_before_the_limit_is_still_rescheduled(self):
        message = make_message(1, attempts=3)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, RuntimeError("down"))

        await build_use_case(store, publisher, max_attempts=5).execute()

        assert 1 in store.rescheduled
        assert store.failed == {}

    async def test_first_failure_goes_straight_to_failed_when_max_attempts_is_one(self):
        message = make_message(1)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, RuntimeError("down"))
        backoff = StubBackoff()

        await build_use_case(store, publisher, backoff, max_attempts=1).execute()

        assert store.failed == {1: "RuntimeError: down"}
        assert store.rescheduled == {}
        assert backoff.calls == []

    async def test_a_poison_message_is_retried_max_attempts_times_then_marked_failed(self):
        message = make_message(1)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, RuntimeError("poison"))
        backoff = StubBackoff()
        use_case = build_use_case(store, publisher, backoff, max_attempts=3)

        executions = 0
        # Hard bound: a regression in the retry ceiling fails instead of looping.
        while 1 not in store.failed and executions < 10:
            await use_case.execute()
            executions += 1

        assert executions == 3
        assert store.failed == {1: "RuntimeError: poison"}
        # Two reschedules (previous-attempt counts 0 and 1), then the final failure.
        assert backoff.calls == [0, 1]
        assert store.commits == 3
        assert await use_case.execute() == 0

    async def test_one_failing_message_does_not_stop_the_rest_of_the_batch(self):
        messages = [make_message(1), make_message(2), make_message(3)]
        store = InMemoryOutboxStore(messages)
        publisher = FakeEventPublisher()
        publisher.fail_with(messages[1].event_id, ValueError("bad"))

        claimed = await build_use_case(store, publisher).execute()

        assert claimed == 3
        assert store.published == [1, 3]
        assert list(store.rescheduled) == [2]
        assert store.commits == 1

    async def test_long_error_is_truncated_to_1000_characters(self):
        message = make_message(1)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, RuntimeError("x" * 5000))

        await build_use_case(store, publisher).execute()

        _, error = store.rescheduled[1]
        assert len(error) == 1000
        assert error.startswith("RuntimeError: xxx")

    async def test_long_error_is_truncated_when_marking_failed_too(self):
        message = make_message(1, attempts=4)
        store = InMemoryOutboxStore([message])
        publisher = FakeEventPublisher()
        publisher.fail_with(message.event_id, RuntimeError("x" * 5000))

        await build_use_case(store, publisher, max_attempts=5).execute()

        assert len(store.failed[1]) == 1000


class TestRelayOutboxBatchUseCaseCancellation:
    async def test_cancelled_error_escapes_and_the_whole_batch_rolls_back(self):
        messages = [make_message(1), make_message(2)]
        store = InMemoryOutboxStore(messages)
        publisher = FakeEventPublisher()
        publisher.fail_with(messages[1].event_id, asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await build_use_case(store, publisher).execute()

        assert store.rollbacks == 1
        assert store.commits == 0
        assert store.published == []
        assert store.rescheduled == {}
        assert store.failed == {}


class TestRelayOutboxBatchUseCaseValidation:
    @pytest.mark.parametrize("batch_size", [0, -1])
    def test_rejects_batch_size_below_one(self, batch_size: int):
        with pytest.raises(ValueError, match="batch_size"):
            build_use_case(InMemoryOutboxStore([]), FakeEventPublisher(), batch_size=batch_size)

    @pytest.mark.parametrize("max_attempts", [0, -1])
    def test_rejects_max_attempts_below_one(self, max_attempts: int):
        with pytest.raises(ValueError, match="max_attempts"):
            build_use_case(InMemoryOutboxStore([]), FakeEventPublisher(), max_attempts=max_attempts)

    @pytest.mark.parametrize("timeout", [0.0, -1.0, math.nan, math.inf])
    def test_rejects_non_positive_or_non_finite_timeout(self, timeout: float):
        with pytest.raises(ValueError, match="publish_timeout_seconds"):
            build_use_case(
                InMemoryOutboxStore([]), FakeEventPublisher(), publish_timeout_seconds=timeout
            )
