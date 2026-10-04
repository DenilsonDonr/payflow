import random

import pytest

from app.shared.outbox.domain.backoff import full_jitter_backoff


class StubRandomSource:
    """Records the bounds it was asked for and returns a chosen value."""

    def __init__(self, returns: float = 0.0) -> None:
        self._returns = returns
        self.calls: list[tuple[float, float]] = []

    def uniform(self, a: float, b: float) -> float:
        self.calls.append((a, b))
        return self._returns


class TestFullJitterBackoff:
    def test_first_failure_waits_up_to_base(self):
        rng = StubRandomSource()

        full_jitter_backoff(0, base_seconds=1.0, cap_seconds=300.0, rng=rng)

        assert rng.calls == [(0, 1.0)]

    @pytest.mark.parametrize(
        ("attempts", "expected_ceiling"),
        [(1, 2.0), (2, 4.0), (3, 8.0)],
    )
    def test_ceiling_doubles_with_each_previous_attempt(
        self, attempts: int, expected_ceiling: float
    ):
        rng = StubRandomSource()

        full_jitter_backoff(attempts, base_seconds=1.0, cap_seconds=300.0, rng=rng)

        assert rng.calls == [(0, expected_ceiling)]

    def test_ceiling_scales_with_base(self):
        rng = StubRandomSource()

        full_jitter_backoff(2, base_seconds=0.5, cap_seconds=300.0, rng=rng)

        assert rng.calls == [(0, 2.0)]

    def test_ceiling_is_capped_once_exponential_exceeds_it(self):
        rng = StubRandomSource()

        full_jitter_backoff(10, base_seconds=1.0, cap_seconds=300.0, rng=rng)

        assert rng.calls == [(0, 300.0)]

    def test_ceiling_equals_cap_when_exponential_matches_it_exactly(self):
        rng = StubRandomSource()

        full_jitter_backoff(3, base_seconds=1.0, cap_seconds=8.0, rng=rng)

        assert rng.calls == [(0, 8.0)]

    def test_very_large_attempts_use_the_cap_without_overflowing(self):
        rng = StubRandomSource()

        full_jitter_backoff(10_000, base_seconds=1.0, cap_seconds=300.0, rng=rng)

        assert rng.calls == [(0, 300.0)]

    def test_returns_exactly_what_the_rng_returns(self):
        rng = StubRandomSource(returns=1.2345)

        result = full_jitter_backoff(2, base_seconds=1.0, cap_seconds=300.0, rng=rng)

        assert result == 1.2345

    @pytest.mark.parametrize("attempts", [0, 1, 5, 50, 10_000])
    def test_real_random_stays_within_zero_and_ceiling(self, attempts: int):
        rng = random.Random(42)
        ceiling = min(300.0, 1.0 * 2**attempts) if attempts < 1000 else 300.0

        delays = [
            full_jitter_backoff(attempts, base_seconds=1.0, cap_seconds=300.0, rng=rng)
            for _ in range(200)
        ]

        assert all(0 <= delay <= ceiling for delay in delays)
        assert len(set(delays)) > 1

    def test_rejects_negative_attempts(self):
        with pytest.raises(ValueError, match="attempts"):
            full_jitter_backoff(-1, base_seconds=1.0, cap_seconds=300.0, rng=StubRandomSource())

    @pytest.mark.parametrize("base_seconds", [0.0, -1.0])
    def test_rejects_non_positive_base(self, base_seconds: float):
        with pytest.raises(ValueError, match="base_seconds"):
            full_jitter_backoff(
                0, base_seconds=base_seconds, cap_seconds=300.0, rng=StubRandomSource()
            )

    def test_rejects_cap_below_base(self):
        with pytest.raises(ValueError, match="cap_seconds"):
            full_jitter_backoff(0, base_seconds=10.0, cap_seconds=5.0, rng=StubRandomSource())

    def test_accepts_cap_equal_to_base(self):
        rng = StubRandomSource()

        full_jitter_backoff(5, base_seconds=2.0, cap_seconds=2.0, rng=rng)

        assert rng.calls == [(0, 2.0)]
