import asyncio
import functools
import logging
import signal
from collections.abc import Callable
from typing import Any, cast

import pytest

from app.shared.outbox.domain.backoff import full_jitter_backoff
from app.shared.outbox.infrastructure import relay_worker

ENV = {
    "OUTBOX_BATCH_SIZE": "7",
    "OUTBOX_POLL_INTERVAL_SECONDS": "0.25",
    "OUTBOX_MAX_ATTEMPTS": "3",
    "OUTBOX_BACKOFF_BASE_SECONDS": "2",
    "OUTBOX_BACKOFF_CAP_SECONDS": "60",
    "OUTBOX_PUBLISH_TIMEOUT_SECONDS": "1.5",
}


class Harness:
    """Records what `main()` wires, with every collaborator stubbed out."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.use_case_kwargs: dict[str, Any] = {}
        self.run_use_case: object = None
        self.run_kwargs: dict[str, Any] = {}
        self.handlers: dict[int, Callable[[], None]] = {}
        self.run_error: Exception | None = None


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> Harness:
    h = Harness()
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)

    def no_basic_config(*args: object, **kwargs: object) -> None:
        pass

    monkeypatch.setattr(logging, "basicConfig", no_basic_config)

    class RecordingUseCase:
        def __init__(self, store: object, publisher: object, **kwargs: Any) -> None:
            h.use_case_kwargs = kwargs

    async def fake_open_pool() -> None:
        h.events.append("open_pool")

    async def fake_close_pool() -> None:
        h.events.append("close_pool")

    async def fake_run(use_case: object, **kwargs: Any) -> None:
        h.events.append("run")
        h.run_use_case = use_case
        h.run_kwargs = kwargs
        if h.run_error is not None:
            raise h.run_error

    class RecordingLoop:
        def add_signal_handler(self, sig: int, callback: Callable[[], None]) -> None:
            h.handlers[sig] = callback

    monkeypatch.setattr(relay_worker, "RelayOutboxBatchUseCase", RecordingUseCase)
    monkeypatch.setattr(relay_worker, "open_pool", fake_open_pool)
    monkeypatch.setattr(relay_worker, "close_pool", fake_close_pool)
    monkeypatch.setattr(relay_worker, "run", fake_run)
    # Patched on the worker module, never on asyncio itself: the event loop running the test
    # must stay real. The real installer runs against a recording loop instead.
    install = relay_worker.install_signal_handlers

    def fake_install(loop: object, stop: asyncio.Event) -> None:
        install(cast(asyncio.AbstractEventLoop, RecordingLoop()), stop)

    monkeypatch.setattr(relay_worker, "install_signal_handlers", fake_install)
    return h


class TestMainWiring:
    async def test_the_use_case_gets_the_settings_loaded_from_the_environment(
        self, harness: Harness
    ):
        await relay_worker.main()

        kwargs = harness.use_case_kwargs
        assert kwargs["batch_size"] == 7
        assert kwargs["max_attempts"] == 3
        assert kwargs["publish_timeout_seconds"] == 1.5

    async def test_the_backoff_uses_the_configured_base_and_cap(self, harness: Harness):
        await relay_worker.main()

        backoff = harness.use_case_kwargs["backoff"]
        assert isinstance(backoff, functools.partial)
        assert backoff.func is full_jitter_backoff
        assert backoff.keywords["base_seconds"] == 2.0
        assert backoff.keywords["cap_seconds"] == 60.0

    async def test_run_gets_the_use_case_and_keyword_pacing(self, harness: Harness):
        await relay_worker.main()

        assert isinstance(harness.run_use_case, relay_worker.RelayOutboxBatchUseCase)
        assert harness.run_kwargs["poll_interval"] == 0.25
        assert harness.run_kwargs["batch_size"] == 7
        assert set(harness.run_kwargs) == {"stop", "poll_interval", "batch_size"}


class TestMainSignals:
    async def test_registers_handlers_for_sigint_and_sigterm_only(self, harness: Harness):
        await relay_worker.main()

        assert set(harness.handlers) == {signal.SIGINT, signal.SIGTERM}

    @pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
    async def test_a_signal_sets_the_stop_event_given_to_run(
        self, harness: Harness, sig: signal.Signals
    ):
        await relay_worker.main()
        stop = harness.run_kwargs["stop"]
        assert isinstance(stop, asyncio.Event)
        assert not stop.is_set()

        harness.handlers[sig]()

        assert stop.is_set()


class TestMainLifecycle:
    async def test_the_pool_is_opened_before_run_and_closed_after(self, harness: Harness):
        await relay_worker.main()

        assert harness.events == ["open_pool", "run", "close_pool"]

    async def test_the_pool_is_closed_when_run_fails(self, harness: Harness):
        harness.run_error = RuntimeError("relay crashed")

        with pytest.raises(RuntimeError, match="relay crashed"):
            await relay_worker.main()

        assert harness.events == ["open_pool", "run", "close_pool"]

    async def test_an_invalid_setting_fails_before_the_pool_is_opened(
        self, harness: Harness, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("OUTBOX_BATCH_SIZE", "0")

        with pytest.raises(ValueError, match="BATCH_SIZE"):
            await relay_worker.main()

        assert harness.events == []
