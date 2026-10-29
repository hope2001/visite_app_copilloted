import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

from app.domain.errors import RateLimitedError


class FailedAttemptLimiter:
    """In-memory sliding-window limiter for failed attempts (single-instance deployments).

    For multiple instances, replace with a shared store such as Redis.
    """

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._monotonic = monotonic
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def ensure_allowed(self, key: str) -> None:
        with self._lock:
            failures = self._prune(key)
            if len(failures) < self._max_attempts:
                return
            retry_after = math.ceil(failures[0] + self._window_seconds - self._monotonic())
        raise RateLimitedError(
            "Too many failed attempts. Please try again later.",
            retry_after_seconds=max(retry_after, 1),
        )

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key).append(self._monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _prune(self, key: str) -> deque[float]:
        failures = self._failures[key]
        cutoff = self._monotonic() - self._window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures
