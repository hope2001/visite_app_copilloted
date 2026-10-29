"""Business-critical visit scenarios not covered by test_visits.py.

Focus: rejected operations must leave no trace (state, timestamps, visitor record and audit
trail unchanged), dates are judged in the site timezone, and every forbidden status
transition is refused through the HTTP API, not only by the domain function.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, User, Visit, Visitor
from tests.conftest import TODAY, TOMORROW, AuthHeaders, FixedClock, VisitFactory, visit_payload

VISITS_URL = "/api/v1/visits"
YESTERDAY = TODAY - timedelta(days=1)
ANY_UUID = "00000000-0000-4000-8000-000000000000"

# Who performs each action by default: front desk for arrivals/departures, registrant for cancel.
DEFAULT_ACTOR = {"check-in": "security", "check-out": "security", "cancel": "employee"}

Act = Callable[..., Response]
Fetch = Callable[[str], dict[str, Any]]


def ts(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def row_counts(db: Session) -> dict[str, int]:
    return {
        model.__name__: db.scalar(select(func.count()).select_from(model)) or 0
        for model in (Visit, Visitor, AuditLog)
    }


def audit_actions(db: Session, visit_id: str) -> list[str]:
    rows = db.scalars(
        select(AuditLog.action)
        .where(AuditLog.visit_id == uuid.UUID(visit_id))
        .order_by(AuditLog.occurred_at, AuditLog.id)
    )
    return [action.value for action in rows]


@pytest.fixture
def act(client: TestClient, users: dict[str, User], auth_headers: AuthHeaders) -> Act:
    def perform(visit_id: str, action: str, as_user: str | None = None) -> Response:
        actor = users[as_user or DEFAULT_ACTOR[action]]
        response: Response = client.post(
            f"{VISITS_URL}/{visit_id}/{action}", headers=auth_headers(actor)
        )
        return response

    return perform


@pytest.fixture
def fetch(client: TestClient, users: dict[str, User], auth_headers: AuthHeaders) -> Fetch:
    def get(visit_id: str) -> dict[str, Any]:
        response = client.get(f"{VISITS_URL}/{visit_id}", headers=auth_headers(users["admin"]))
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    return get


# ---- Successful registration ----------------------------------------------------------------


def test_successful_registration_is_persisted_exactly_as_returned(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    fetch: Fetch,
) -> None:
    payload = visit_payload(
        expected_date=TOMORROW.isoformat(),
        host_id=str(users["employee"].id),
        purpose="  Contract signature  ",
    )

    response = client.post(VISITS_URL, json=payload, headers=auth_headers(users["admin"]))

    assert response.status_code == 201
    created = response.json()
    assert created == fetch(created["id"])
    assert created["status"] == "EXPECTED"
    assert created["expected_date"] == TOMORROW.isoformat()
    assert created["purpose"] == "Contract signature"
    assert created["host"]["id"] == str(users["employee"].id)
    assert created["registered_by"]["id"] == str(users["admin"].id)
    assert created["visitor"] | {"id": None} == {
        "id": None,
        "full_name": "Jane Doe",
        "email": "jane.doe@contoso.com",
        "phone": "+33 6 12 34 56 78",
        "company": "Contoso",
    }
    assert (created["checked_in_at"], created["checked_out_at"], created["cancelled_at"]) == (
        None,
        None,
        None,
    )


def test_registration_is_audited_with_the_registrant_as_actor(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit(host_id=str(users["other_employee"].id))

    trail = client.get(
        f"{VISITS_URL}/{visit['id']}/audit", headers=auth_headers(users["security"])
    ).json()

    assert len(trail) == 1
    assert trail[0]["action"] == "VISIT_CREATED"
    assert trail[0]["performed_by"]["id"] == str(users["employee"].id)
    assert (trail[0]["from_status"], trail[0]["to_status"]) == (None, "EXPECTED")


# ---- Invalid registration -------------------------------------------------------------------


def _without_visitor() -> dict[str, Any]:
    payload = visit_payload()
    del payload["visitor"]
    return payload


def _with_visitor(**changes: Any) -> dict[str, Any]:
    payload = visit_payload()
    payload["visitor"] = payload["visitor"] | changes
    return payload


V = "VALIDATION_ERROR"

# (id, payload, expected error code, offending field)
INVALID_REGISTRATIONS: list[tuple[str, dict[str, Any], str, str]] = [
    ("missing-visitor", _without_visitor(), V, "visitor"),
    ("blank-name", _with_visitor(full_name="   "), V, "visitor.full_name"),
    ("blank-company", _with_visitor(company=""), V, "visitor.company"),
    ("bad-email", _with_visitor(email="jane@"), V, "visitor.email"),
    ("name-too-long", _with_visitor(full_name="x" * 121), V, "visitor.full_name"),
    ("purpose-too-long", visit_payload(purpose="x" * 501), V, "purpose"),
    ("malformed-date", visit_payload(expected_date="28/10/2026"), V, "expected_date"),
    ("malformed-host", visit_payload(host_id="not-a-uuid"), V, "host_id"),
    ("unknown-host", visit_payload(host_id=str(uuid.uuid4())), "HOST_NOT_FOUND", "host_id"),
    ("mass-assign-registrant", visit_payload(registered_by_id=ANY_UUID), V, "registered_by_id"),
    ("mass-assign-check-in", visit_payload(checked_in_at="2026-10-28T08:00Z"), V, "checked_in_at"),
    ("mass-assign-id", visit_payload(id=ANY_UUID), V, "id"),
]


@pytest.mark.parametrize(
    ("payload", "code", "field"),
    [pytest.param(*case[1:], id=case[0]) for case in INVALID_REGISTRATIONS],
)
def test_invalid_registration_is_rejected_without_side_effects(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
    payload: dict[str, Any],
    code: str,
    field: str,
) -> None:
    before = row_counts(db)

    response = client.post(VISITS_URL, json=payload, headers=auth_headers(users["employee"]))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == code
    assert field in {detail["field"] for detail in error["details"]}
    assert row_counts(db) == before


@pytest.mark.parametrize("body", ["", "not json", "[]"], ids=["empty", "not-json", "array"])
def test_unparseable_registration_body_is_rejected(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders, body: str
) -> None:
    headers = auth_headers(users["employee"]) | {"Content-Type": "application/json"}

    response = client.post(VISITS_URL, content=body, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_rejected_registration_does_not_overwrite_returning_visitor(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
) -> None:
    create_visit()
    changed = visit_payload()["visitor"] | {"full_name": "Someone Else", "company": "Other Co"}

    for rejected in (
        visit_payload(visitor=changed, expected_date=YESTERDAY.isoformat()),
        visit_payload(visitor=changed, host_id=str(users["security"].id)),
    ):
        response = client.post(VISITS_URL, json=rejected, headers=auth_headers(users["employee"]))
        assert response.status_code == 422

    visitor = db.scalars(select(Visitor)).one()
    assert (visitor.full_name, visitor.company) == ("Jane Doe", "Contoso")


# ---- Past visit date ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expected_date",
    [YESTERDAY, TODAY - timedelta(days=365), date(2000, 1, 1)],
    ids=["yesterday", "last-year", "long-ago"],
)
def test_past_visit_date_is_rejected_without_side_effects(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
    expected_date: date,
) -> None:
    response = client.post(
        VISITS_URL,
        json=visit_payload(expected_date=expected_date.isoformat()),
        headers=auth_headers(users["employee"]),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in error["details"]] == ["expected_date"]
    assert row_counts(db) == {"Visit": 0, "Visitor": 0, "AuditLog": 0}


# Europe/Paris is UTC+1 after the DST change on 2026-10-25.
@pytest.mark.parametrize(
    ("now_utc", "expected_date", "status"),
    [
        # 23:30 UTC on the 28th is already the 29th in Paris: the 28th is now in the past.
        (datetime(2026, 10, 28, 23, 30, tzinfo=UTC), date(2026, 10, 28), 422),
        (datetime(2026, 10, 28, 23, 30, tzinfo=UTC), date(2026, 10, 29), 201),
        # 23:30 UTC on the 27th is 00:30 on the 28th in Paris: the 27th is in the past.
        (datetime(2026, 10, 27, 23, 30, tzinfo=UTC), date(2026, 10, 27), 422),
        # Just before local midnight, today is still accepted.
        (datetime(2026, 10, 28, 22, 59, tzinfo=UTC), date(2026, 10, 28), 201),
    ],
    ids=["utc-today-is-local-yesterday", "local-today", "local-yesterday", "last-minute-of-day"],
)
def test_past_date_is_judged_in_site_timezone(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    clock: FixedClock,
    now_utc: datetime,
    expected_date: date,
    status: int,
) -> None:
    clock.set(now_utc)

    response = client.post(
        VISITS_URL,
        json=visit_payload(expected_date=expected_date.isoformat()),
        headers=auth_headers(users["employee"]),
    )

    assert response.status_code == status, response.text


# ---- Check-in -------------------------------------------------------------------------------


@pytest.mark.parametrize("operator", ["security", "admin"])
def test_check_in_records_arrival_time_and_operator(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    clock: FixedClock,
    act: Act,
    fetch: Fetch,
    operator: str,
) -> None:
    visit = create_visit()
    clock.advance(timedelta(minutes=12))

    response = act(visit["id"], "check-in", as_user=operator)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CHECKED_IN"
    assert ts(body["checked_in_at"]) == clock.now()
    assert body["checked_out_at"] is None
    assert fetch(visit["id"]) == body
    trail = client.get(
        f"{VISITS_URL}/{visit['id']}/audit", headers=auth_headers(users["admin"])
    ).json()
    assert trail[-1]["performed_by"]["id"] == str(users[operator].id)
    assert ts(trail[-1]["occurred_at"]) == clock.now()


def test_duplicate_check_in_keeps_original_arrival_time(
    create_visit: VisitFactory, clock: FixedClock, act: Act, fetch: Fetch, db: Session
) -> None:
    visit = create_visit()
    clock.advance(timedelta(minutes=5))
    first = act(visit["id"], "check-in").json()
    clock.advance(timedelta(minutes=30))

    duplicate = act(visit["id"], "check-in", as_user="admin")

    assert duplicate.status_code == 409
    error = duplicate.json()["error"]
    assert error["code"] == "VISIT_INVALID_TRANSITION"
    assert "CHECKED_IN" in error["message"]
    assert fetch(visit["id"]) == first
    assert audit_actions(db, visit["id"]) == ["VISIT_CREATED", "CHECKED_IN"]


# ---- Check-out ------------------------------------------------------------------------------


def test_check_out_records_departure_and_keeps_arrival(
    create_visit: VisitFactory, clock: FixedClock, act: Act, fetch: Fetch, db: Session
) -> None:
    visit = create_visit()
    clock.advance(timedelta(minutes=5))
    arrived = ts(act(visit["id"], "check-in").json()["checked_in_at"])
    clock.advance(timedelta(hours=3, minutes=5))

    response = act(visit["id"], "check-out")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CHECKED_OUT"
    assert ts(body["checked_in_at"]) == arrived
    assert ts(body["checked_out_at"]) == clock.now()
    assert fetch(visit["id"]) == body
    assert audit_actions(db, visit["id"]) == ["VISIT_CREATED", "CHECKED_IN", "CHECKED_OUT"]


def test_visitor_still_on_site_after_midnight_can_check_out(
    create_visit: VisitFactory, clock: FixedClock, act: Act
) -> None:
    visit = create_visit()
    act(visit["id"], "check-in")
    clock.set(datetime(TOMORROW.year, TOMORROW.month, TOMORROW.day, 7, 0, tzinfo=UTC))

    response = act(visit["id"], "check-out")

    assert response.status_code == 200
    assert response.json()["status"] == "CHECKED_OUT"


def test_duplicate_check_out_keeps_original_departure_time(
    create_visit: VisitFactory, clock: FixedClock, act: Act, fetch: Fetch, db: Session
) -> None:
    visit = create_visit()
    clock.advance(timedelta(minutes=5))
    act(visit["id"], "check-in")
    clock.advance(timedelta(hours=1))
    first = act(visit["id"], "check-out").json()
    clock.advance(timedelta(minutes=10))

    duplicate = act(visit["id"], "check-out")

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "VISIT_INVALID_TRANSITION"
    assert fetch(visit["id"]) == first
    assert audit_actions(db, visit["id"]) == ["VISIT_CREATED", "CHECKED_IN", "CHECKED_OUT"]


def test_check_out_before_check_in_leaves_visit_untouched(
    create_visit: VisitFactory, act: Act, fetch: Fetch, db: Session
) -> None:
    visit = create_visit()

    response = act(visit["id"], "check-out")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "VISIT_INVALID_TRANSITION"
    assert "EXPECTED" in error["message"]
    assert fetch(visit["id"]) == visit
    assert audit_actions(db, visit["id"]) == ["VISIT_CREATED"]
    # The visit is still usable afterwards.
    assert act(visit["id"], "check-in").status_code == 200


# ---- Invalid status transitions through the API ---------------------------------------------

SETUP_STEPS = {
    "CHECKED_IN": ["check-in"],
    "CHECKED_OUT": ["check-in", "check-out"],
    "CANCELLED": ["cancel"],
}

FORBIDDEN_TRANSITIONS = [
    ("CHECKED_IN", "check-in"),
    ("CHECKED_IN", "cancel"),
    ("CHECKED_OUT", "check-in"),
    ("CHECKED_OUT", "check-out"),
    ("CHECKED_OUT", "cancel"),
    ("CANCELLED", "check-in"),
    ("CANCELLED", "check-out"),
    ("CANCELLED", "cancel"),
]


@pytest.mark.parametrize(("status", "action"), FORBIDDEN_TRANSITIONS)
@pytest.mark.parametrize("actor", ["default", "admin"])
def test_forbidden_transition_is_rejected_and_changes_nothing(
    create_visit: VisitFactory,
    clock: FixedClock,
    act: Act,
    fetch: Fetch,
    db: Session,
    status: str,
    action: str,
    actor: str,
) -> None:
    visit = create_visit()
    for step in SETUP_STEPS[status]:
        clock.advance(timedelta(minutes=5))
        assert act(visit["id"], step).status_code == 200
    before = fetch(visit["id"])
    trail_before = audit_actions(db, visit["id"])
    clock.advance(timedelta(minutes=1))

    response = act(visit["id"], action, as_user=None if actor == "default" else actor)

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "VISIT_INVALID_TRANSITION"
    assert before["status"] == status
    assert fetch(visit["id"]) == before
    assert audit_actions(db, visit["id"]) == trail_before


def test_cancelled_visit_on_another_day_reports_the_status_problem_first(
    create_visit: VisitFactory, act: Act
) -> None:
    visit = create_visit(expected_date=TOMORROW.isoformat())
    act(visit["id"], "cancel")

    response = act(visit["id"], "check-in")

    assert response.json()["error"]["code"] == "VISIT_INVALID_TRANSITION"


# ---- Visit not found ------------------------------------------------------------------------

ACTION_ENDPOINTS = [
    ("POST", "check-in", "security"),
    ("POST", "check-out", "security"),
    ("POST", "cancel", "employee"),
    ("GET", "audit", "security"),
]


@pytest.mark.parametrize(("method", "endpoint", "role"), ACTION_ENDPOINTS)
def test_unknown_visit_returns_404_on_every_action(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
    method: str,
    endpoint: str,
    role: str,
) -> None:
    response = client.request(
        method, f"{VISITS_URL}/{uuid.uuid4()}/{endpoint}", headers=auth_headers(users[role])
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VISIT_NOT_FOUND"
    assert row_counts(db)["AuditLog"] == 0


@pytest.mark.parametrize(("method", "endpoint", "role"), ACTION_ENDPOINTS)
def test_malformed_visit_id_is_a_validation_error_on_every_action(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    method: str,
    endpoint: str,
    role: str,
) -> None:
    response = client.request(
        method, f"{VISITS_URL}/1%20OR%201=1/{endpoint}", headers=auth_headers(users[role])
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "visit_id"


def test_employee_cannot_learn_that_someone_elses_visit_exists(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    act: Act,
    fetch: Fetch,
) -> None:
    visit = create_visit()
    unknown = client.post(
        f"{VISITS_URL}/{uuid.uuid4()}/cancel", headers=auth_headers(users["other_employee"])
    )

    hidden = act(visit["id"], "cancel", as_user="other_employee")

    assert hidden.status_code == unknown.status_code == 404
    assert hidden.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert fetch(visit["id"])["status"] == "EXPECTED"
