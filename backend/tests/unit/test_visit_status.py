import pytest

from app.domain.enums import VisitStatus
from app.domain.errors import InvalidStateTransitionError
from app.domain.visit_status import ALLOWED_TRANSITIONS, can_transition, ensure_transition

ALLOWED = {
    (VisitStatus.EXPECTED, VisitStatus.CHECKED_IN),
    (VisitStatus.EXPECTED, VisitStatus.CANCELLED),
    (VisitStatus.CHECKED_IN, VisitStatus.CHECKED_OUT),
}
ALL_PAIRS = [(current, target) for current in VisitStatus for target in VisitStatus]


def test_every_status_has_a_transition_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(VisitStatus)


@pytest.mark.parametrize(("current", "target"), ALL_PAIRS)
def test_can_transition_matches_the_specification(
    current: VisitStatus, target: VisitStatus
) -> None:
    assert can_transition(current, target) is ((current, target) in ALLOWED)


@pytest.mark.parametrize(("current", "target"), sorted(set(ALL_PAIRS) - ALLOWED))
def test_ensure_transition_rejects_forbidden_moves(
    current: VisitStatus, target: VisitStatus
) -> None:
    with pytest.raises(InvalidStateTransitionError) as error:
        ensure_transition(current, target)
    assert current.value in error.value.message


@pytest.mark.parametrize(("current", "target"), sorted(ALLOWED))
def test_ensure_transition_accepts_allowed_moves(current: VisitStatus, target: VisitStatus) -> None:
    ensure_transition(current, target)


@pytest.mark.parametrize("terminal", [VisitStatus.CHECKED_OUT, VisitStatus.CANCELLED])
def test_terminal_states_have_no_outgoing_transitions(terminal: VisitStatus) -> None:
    assert ALLOWED_TRANSITIONS[terminal] == frozenset()
