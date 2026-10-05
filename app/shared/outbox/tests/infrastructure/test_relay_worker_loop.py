import asyncio
import logging
import time

import pytest

from app.shared.outbox.infrastructure import relay_worker
from app.shared.outbox.infrastructure.relay_worker import run

BATCH_SIZE = 3


class ScriptedUseCase:
    """Returns (or raises) the scripted outcomes in order; sets `stop` after the last one."""

    def __init__(self, script: list[int | Exception], stop: asyncio.Event | None = None) -> None:
        self._script = list(script)
        self._stop = stop
        self.call_times: list[float] = []

    async def execute(self) -> int:
        self.call_times.append(time.perf_counter())
        outcome = self._script.pop(0)
        if not self._script and self._stop is not None:
            self._stop.set()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class HangingUseCase:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self) -> int:
        self.calls += 1
        await asyncio.sleep(5)
        return 0


class TestRunBatchPacing:
    async def test_a_full_batch_loops_again_without_waiting(self):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([BATCH_SIZE, BATCH_SIZE, 1], stop)

        await asyncio.wait_for(
            run(use_case, stop=stop, poll_interval=5.0, batch_size=BATCH_SIZE), timeout=1
        )

        assert len(use_case.call_times) == 3

    async def test_a_partial_batch_waits_the_poll_interval(self):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([BATCH_SIZE - 1, 0], stop)

        await asyncio.wait_for(
            run(use_case, stop=stop, poll_interval=0.05, batch_size=BATCH_SIZE), timeout=1
        )

        gap = use_case.call_times[1] - use_case.call_times[0]
        assert gap >= 0.04

    async def test_an_empty_batch_waits_the_poll_interval(self):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([0, 0], stop)

        await asyncio.wait_for(
            run(use_case, stop=stop, poll_interval=0.05, batch_size=BATCH_SIZE), timeout=1
        )

        assert use_case.call_times[1] - use_case.call_times[0] >= 0.04


class TestRunStopping:
    async def test_does_nothing_when_already_stopped(self):
        stop = asyncio.Event()
        stop.set()
        use_case = ScriptedUseCase([0])

        await asyncio.wait_for(
            run(use_case, stop=stop, poll_interval=5.0, batch_size=BATCH_SIZE), timeout=1
        )

        assert use_case.call_times == []

    async def test_setting_the_stop_event_ends_the_loop_during_the_wait(self):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([0, 0])
        task = asyncio.create_task(
            run(use_case, stop=stop, poll_interval=30.0, batch_size=BATCH_SIZE)
        )
        while not use_case.call_times:
            await asyncio.sleep(0)

        stop.set()

        await asyncio.wait_for(task, timeout=1)
        assert len(use_case.call_times) == 1

    async def test_a_full_batch_does_not_outrun_the_stop_event(self):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([BATCH_SIZE, BATCH_SIZE], stop)

        await asyncio.wait_for(
            run(use_case, stop=stop, poll_interval=5.0, batch_size=BATCH_SIZE), timeout=1
        )

        assert len(use_case.call_times) == 2

    async def test_the_in_flight_batch_finishes_before_the_loop_exits(self):
        stop = asyncio.Event()
        finished: list[bool] = []

        class SlowUseCase:
            async def execute(self) -> int:
                stop.set()  # shutdown requested while the batch is running
                await asyncio.sleep(0.02)
                finished.append(True)
                return BATCH_SIZE

        await asyncio.wait_for(
            run(SlowUseCase(), stop=stop, poll_interval=5.0, batch_size=BATCH_SIZE), timeout=1
        )

        assert finished == [True]


class TestRunFailureHandling:
    async def test_an_exception_is_logged_and_the_loop_continues(
        self, caplog: pytest.LogCaptureFixture
    ):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([RuntimeError("db down"), 0], stop)

        with caplog.at_level(logging.ERROR, logger=relay_worker.__name__):
            await asyncio.wait_for(
                run(use_case, stop=stop, poll_interval=0.01, batch_size=BATCH_SIZE), timeout=1
            )

        assert len(use_case.call_times) == 2
        records = [r for r in caplog.records if r.name == relay_worker.__name__]
        assert len(records) == 1
        assert records[0].exc_info is not None
        assert "db down" in str(records[0].exc_info[1])

    async def test_waits_the_poll_interval_after_a_failure(self):
        stop = asyncio.Event()
        use_case = ScriptedUseCase([RuntimeError("boom"), 0], stop)

        await asyncio.wait_for(
            run(use_case, stop=stop, poll_interval=0.05, batch_size=BATCH_SIZE), timeout=1
        )

        assert use_case.call_times[1] - use_case.call_times[0] >= 0.04

    async def test_cancellation_propagates(self):
        stop = asyncio.Event()
        use_case = HangingUseCase()
        task = asyncio.create_task(
            run(use_case, stop=stop, poll_interval=0.01, batch_size=BATCH_SIZE)
        )
        while use_case.calls == 0:
            await asyncio.sleep(0)

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
