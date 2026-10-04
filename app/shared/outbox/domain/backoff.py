from typing import Protocol


class RandomSource(Protocol):
    """Structural subset of random.Random, so tests can inject a stub."""

    def uniform(self, a: float, b: float) -> float: ...


def full_jitter_backoff(
    attempts: int,
    *,
    base_seconds: float,
    cap_seconds: float,
    rng: RandomSource,
) -> float:
    """Seconds to wait before retrying a row that already failed `attempts` times.

    The delay is drawn uniformly from [0, min(cap, base * 2**attempts)]. The
    randomness is the point: rows that failed together during a broker outage
    would otherwise share the same `available_at` and retry in lockstep.
    """
    if attempts < 0:
        raise ValueError(f"attempts must be >= 0, got {attempts}")
    if base_seconds <= 0:
        raise ValueError(f"base_seconds must be > 0, got {base_seconds}")
    if cap_seconds < base_seconds:
        raise ValueError(f"cap_seconds ({cap_seconds}) must be >= base_seconds ({base_seconds})")

    # Double step by step and stop at the cap: `base * 2**attempts` raises
    # OverflowError for huge attempts, and the loop ends after a few steps.
    ceiling = base_seconds
    for _ in range(attempts):
        ceiling *= 2
        if ceiling >= cap_seconds:
            return rng.uniform(0, cap_seconds)

    return rng.uniform(0, min(ceiling, cap_seconds))
