from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from app.domain.enums import VisitStatus
from app.domain.errors import InvalidStateTransitionError

ALLOWED_TRANSITIONS: Final[Mapping[VisitStatus, frozenset[VisitStatus]]] = MappingProxyType(
    {
        VisitStatus.EXPECTED: frozenset({VisitStatus.CHECKED_IN, VisitStatus.CANCELLED}),
        VisitStatus.CHECKED_IN: frozenset({VisitStatus.CHECKED_OUT}),
        VisitStatus.CHECKED_OUT: frozenset(),
        VisitStatus.CANCELLED: frozenset(),
    }
)


def can_transition(current: VisitStatus, target: VisitStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: VisitStatus, target: VisitStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStateTransitionError(
            f"A visit cannot move from {current.value} to {target.value}."
        )
