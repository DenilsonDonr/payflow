"""Entrypoint of the outbox relay: `python -m app.shared.outbox.infrastructure.relay_worker`."""

import asyncio
import contextlib
import functools
import logging
import math
import os
import random
import signal
from dataclasses import dataclass
from typing import Protocol, Self

from app.shared.outbox.application.relay_outbox_batch_use_case import RelayOutboxBatchUseCase
from app.shared.outbox.domain.backoff import full_jitter_backoff
from app.shared.outbox.infrastructure.persistence.postgres_outbox_store import PostgresOutboxStore
from app.shared.outbox.infrastructure.publishing.logging_event_publisher import (
    LoggingEventPublisher,
)
from app.shared.persistence.postgres_connection import ConnectionDB, close_pool, open_pool

logger = logging.getLogger(__name__)


def _positive_int(name: str, raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}")
    return value


def _positive_finite_float(name: str, raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None
    # NaN slips past every `<=` comparison and inf means "never".
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and > 0, got {raw!r}")
    return value


@dataclass(frozen=True)
class RelaySettings:
    """Relay tuning, validated when built so a bad value stops the worker on boot.

    A batch holds its transaction (and its row locks) open while it publishes, up to
    `batch_size * publish_timeout_seconds` in the worst case: with the defaults 20 * 2s = 40s.
    A long transaction pins the xmin horizon and delays VACUUM, so raise either value knowingly.
    """

    batch_size: int = 20
    poll_interval_seconds: float = 1.0
    max_attempts: int = 10
    backoff_base_seconds: float = 1.0
    backoff_cap_seconds: float = 300.0
    publish_timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        for name in ("poll_interval_seconds", "publish_timeout_seconds", "backoff_base_seconds"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and > 0, got {value}")
        if not math.isfinite(self.backoff_cap_seconds) or (
            self.backoff_cap_seconds < self.backoff_base_seconds
        ):
            raise ValueError(
                f"backoff_cap_seconds ({self.backoff_cap_seconds}) must be finite and >= "
                f"backoff_base_seconds ({self.backoff_base_seconds})"
            )

    @classmethod
    def from_env(cls) -> Self:
        defaults = cls()
        env = os.environ.get
        return cls(
            batch_size=_positive_int(
                "OUTBOX_BATCH_SIZE", env("OUTBOX_BATCH_SIZE", str(defaults.batch_size))
            ),
            poll_interval_seconds=_positive_finite_float(
                "OUTBOX_POLL_INTERVAL_SECONDS",
                env("OUTBOX_POLL_INTERVAL_SECONDS", str(defaults.poll_interval_seconds)),
            ),
            max_attempts=_positive_int(
                "OUTBOX_MAX_ATTEMPTS", env("OUTBOX_MAX_ATTEMPTS", str(defaults.max_attempts))
            ),
            backoff_base_seconds=_positive_finite_float(
                "OUTBOX_BACKOFF_BASE_SECONDS",
                env("OUTBOX_BACKOFF_BASE_SECONDS", str(defaults.backoff_base_seconds)),
            ),
            backoff_cap_seconds=_positive_finite_float(
                "OUTBOX_BACKOFF_CAP_SECONDS",
                env("OUTBOX_BACKOFF_CAP_SECONDS", str(defaults.backoff_cap_seconds)),
            ),
            publish_timeout_seconds=_positive_finite_float(
                "OUTBOX_PUBLISH_TIMEOUT_SECONDS",
                env("OUTBOX_PUBLISH_TIMEOUT_SECONDS", str(defaults.publish_timeout_seconds)),
            ),
        )


class BatchRunner(Protocol):
    async def execute(self) -> int: ...


async def _wait_for_stop(stop: asyncio.Event, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


async def run(
    use_case: BatchRunner, stop: asyncio.Event, poll_interval: float, batch_size: int
) -> None:
    """Relay batches until `stop` is set.

    A full batch means more rows are probably waiting, so the next batch starts at once;
    otherwise the loop sleeps `poll_interval` (cut short by `stop`). A batch in flight always
    finishes before the loop looks at `stop`. A failed batch is logged and retried after the
    same sleep; cancellation is never swallowed.
    """
    while not stop.is_set():
        try:
            claimed = await use_case.execute()
        except Exception:
            logger.exception("outbox relay batch failed; retrying in %ss", poll_interval)
            await _wait_for_stop(stop, poll_interval)
            continue
        if claimed < batch_size:
            await _wait_for_stop(stop, poll_interval)


def warn_about_stand_in_publisher() -> None:
    logger.warning(
        "LoggingEventPublisher is a stand-in: events are marked published but delivered "
        "nowhere. Replace it with a real broker adapter before relying on the outbox."
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = RelaySettings.from_env()
    backoff = functools.partial(
        full_jitter_backoff,
        base_seconds=settings.backoff_base_seconds,
        cap_seconds=settings.backoff_cap_seconds,
        rng=random.Random(),
    )
    backoff(0)  # smoke check: a bad policy must crash here, not poison a batch later
    use_case = RelayOutboxBatchUseCase(
        PostgresOutboxStore(ConnectionDB()),
        LoggingEventPublisher(),
        batch_size=settings.batch_size,
        max_attempts=settings.max_attempts,
        publish_timeout_seconds=settings.publish_timeout_seconds,
        backoff=backoff,
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    warn_about_stand_in_publisher()
    await open_pool()
    try:
        logger.info("outbox relay started: %s", settings)
        await run(use_case, stop, settings.poll_interval_seconds, settings.batch_size)
    finally:
        await close_pool()
        logger.info("outbox relay stopped")


if __name__ == "__main__":
    asyncio.run(main())
