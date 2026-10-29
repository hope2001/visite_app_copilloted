from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    """Source of the current time. Injected so business rules stay deterministic in tests."""

    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def local_today(clock: Clock, timezone: ZoneInfo) -> date:
    return clock.now().astimezone(timezone).date()
