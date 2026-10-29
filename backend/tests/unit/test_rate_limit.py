import pytest

from app.core.rate_limit import FailedAttemptLimiter
from app.domain.errors import RateLimitedError


class FakeMonotonic:
    def __init__(self) -> None:
        self.value = 1000.0

    def __call__(self) -> float:
        return self.value


@pytest.fixture
def monotonic() -> FakeMonotonic:
    return FakeMonotonic()


@pytest.fixture
def limiter(monotonic: FakeMonotonic) -> FailedAttemptLimiter:
    return FailedAttemptLimiter(max_attempts=2, window_seconds=60, monotonic=monotonic)


def test_blocks_after_max_failures(limiter: FailedAttemptLimiter) -> None:
    limiter.record_failure("k")
    limiter.record_failure("k")

    with pytest.raises(RateLimitedError) as error:
        limiter.ensure_allowed("k")
    assert error.value.retry_after_seconds == 60


def test_window_expiry_allows_again(
    limiter: FailedAttemptLimiter, monotonic: FakeMonotonic
) -> None:
    limiter.record_failure("k")
    limiter.record_failure("k")
    monotonic.value += 61

    limiter.ensure_allowed("k")


def test_reset_and_keys_are_independent(limiter: FailedAttemptLimiter) -> None:
    limiter.record_failure("a")
    limiter.record_failure("a")
    limiter.ensure_allowed("b")

    limiter.reset("a")
    limiter.ensure_allowed("a")
