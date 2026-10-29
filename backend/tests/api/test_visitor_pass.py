"""QR visitor pass: issued after registration, scanned by the front desk to find the visit.

A scan only identifies the visit; admission still goes through the normal check-in endpoint.
"""

import logging
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.visitor_pass import PASS_PREFIX, VisitorPassCodec
from app.models import AuditLog, User
from tests.conftest import TOMORROW, AuthHeaders, VisitFactory

VISITS_URL = "/api/v1/visits"
LOOKUP_URL = f"{VISITS_URL}/pass-lookup"


def get_pass(
    client: TestClient, auth_headers: AuthHeaders, user: User, visit_id: str
) -> dict[str, Any]:
    response = client.get(f"{VISITS_URL}/{visit_id}/pass", headers=auth_headers(user))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def audit_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(AuditLog)) or 0


# ---- Issuing the pass -----------------------------------------------------------------------


def test_registered_visit_has_a_unique_pass_without_personal_data(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    settings: Settings,
) -> None:
    first = create_visit()
    second = create_visit()

    issued = get_pass(client, auth_headers, users["employee"], first["id"])

    assert issued["visit_id"] == first["id"]
    assert issued["code"].startswith(PASS_PREFIX)
    assert VisitorPassCodec(settings.jwt_secret_key).decode(issued["code"]) == uuid.UUID(
        first["id"]
    )
    assert issued["code"] != get_pass(client, auth_headers, users["employee"], second["id"])["code"]
    for personal in ("Jane", "Doe", "Contoso", "jane.doe", "+33"):
        assert personal.upper() not in issued["code"]


def test_pass_is_stable_so_it_can_be_shown_again(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit()

    by_registrant = get_pass(client, auth_headers, users["employee"], visit["id"])
    again = get_pass(client, auth_headers, users["employee"], visit["id"])
    by_admin = get_pass(client, auth_headers, users["admin"], visit["id"])

    assert by_registrant == again == by_admin


def test_host_can_get_the_pass_of_a_visit_registered_for_them(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit(host_id=str(users["other_employee"].id))

    issued = get_pass(client, auth_headers, users["other_employee"], visit["id"])

    assert issued["visit_id"] == visit["id"]


def test_unrelated_employee_cannot_get_a_pass(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit()

    hidden = client.get(
        f"{VISITS_URL}/{visit['id']}/pass", headers=auth_headers(users["other_employee"])
    )
    unknown = client.get(
        f"{VISITS_URL}/{uuid.uuid4()}/pass", headers=auth_headers(users["other_employee"])
    )

    assert hidden.status_code == unknown.status_code == 404
    assert hidden.json()["error"]["code"] == "VISIT_NOT_FOUND"
    assert PASS_PREFIX not in hidden.text


# ---- Scanning the pass at the front desk ----------------------------------------------------


@pytest.mark.parametrize("operator", ["security", "admin"])
def test_scanned_pass_identifies_the_visit_without_checking_in(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
    caplog: pytest.LogCaptureFixture,
    operator: str,
) -> None:
    visit = create_visit()
    code = get_pass(client, auth_headers, users["employee"], visit["id"])["code"]

    with caplog.at_level(logging.INFO):
        response = client.post(
            LOOKUP_URL, json={"code": code}, headers=auth_headers(users[operator])
        )

    assert response.status_code == 200
    assert response.json() == visit
    assert response.json()["status"] == "EXPECTED"
    assert audit_count(db) == 1
    assert "Visitor pass resolved" in caplog.messages
    assert code not in caplog.text


def test_pass_scan_then_normal_check_in(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
) -> None:
    visit = create_visit()
    code = get_pass(client, auth_headers, users["employee"], visit["id"])["code"]
    desk = auth_headers(users["security"])

    found = client.post(LOOKUP_URL, json={"code": code}, headers=desk).json()
    checked_in = client.post(f"{VISITS_URL}/{found['id']}/check-in", headers=desk)

    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "CHECKED_IN"
    trail = client.get(f"{VISITS_URL}/{visit['id']}/audit", headers=desk).json()
    assert [entry["action"] for entry in trail] == ["VISIT_CREATED", "CHECKED_IN"]
    assert trail[-1]["performed_by"]["id"] == str(users["security"].id)

    # Scanning the same pass again shows the visitor is already in, and cannot re-admit them.
    rescanned = client.post(LOOKUP_URL, json={"code": code}, headers=desk).json()
    assert rescanned["status"] == "CHECKED_IN"
    again = client.post(f"{VISITS_URL}/{rescanned['id']}/check-in", headers=desk)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "VISIT_INVALID_TRANSITION"
    assert audit_count(db) == 2


def test_scanner_input_noise_is_tolerated(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit()
    code = get_pass(client, auth_headers, users["employee"], visit["id"])["code"]

    response = client.post(
        LOOKUP_URL, json={"code": f"  {code.lower()}\r\n"}, headers=auth_headers(users["security"])
    )

    assert response.status_code == 200
    assert response.json()["id"] == visit["id"]


def test_pass_of_cancelled_visit_no_longer_admits(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit()
    code = get_pass(client, auth_headers, users["employee"], visit["id"])["code"]
    client.post(f"{VISITS_URL}/{visit['id']}/cancel", headers=auth_headers(users["employee"]))
    desk = auth_headers(users["security"])

    found = client.post(LOOKUP_URL, json={"code": code}, headers=desk).json()
    check_in = client.post(f"{VISITS_URL}/{found['id']}/check-in", headers=desk)

    assert found["status"] == "CANCELLED"
    assert check_in.status_code == 409
    assert check_in.json()["error"]["code"] == "VISIT_INVALID_TRANSITION"


def test_pass_presented_on_the_wrong_day_does_not_admit(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit(expected_date=TOMORROW.isoformat())
    code = get_pass(client, auth_headers, users["employee"], visit["id"])["code"]
    desk = auth_headers(users["security"])

    found = client.post(LOOKUP_URL, json={"code": code}, headers=desk).json()
    check_in = client.post(f"{VISITS_URL}/{found['id']}/check-in", headers=desk)

    assert found["expected_date"] == TOMORROW.isoformat()
    assert check_in.status_code == 409
    assert check_in.json()["error"]["code"] == "VISIT_NOT_DUE_TODAY"


def _forged(settings: Settings, visit_id: str) -> str:
    return VisitorPassCodec("attacker-guess-0123456789-abcdefghij").encode(uuid.UUID(visit_id))


def _altered(settings: Settings, visit_id: str) -> str:
    code = VisitorPassCodec(settings.jwt_secret_key).encode(uuid.UUID(visit_id))
    return code[:-2] + ("AA" if code[-2:] != "AA" else "BA")


def _unknown_visit(settings: Settings, visit_id: str) -> str:
    return VisitorPassCodec(settings.jwt_secret_key).encode(uuid.uuid4())


def _raw_visit_id(settings: Settings, visit_id: str) -> str:
    return visit_id


def _garbage(settings: Settings, visit_id: str) -> str:
    return "https://evil.example/<script>"


@pytest.mark.parametrize(
    "make_code",
    [_forged, _altered, _unknown_visit, _raw_visit_id, _garbage],
    ids=["forged-key", "altered", "unknown-visit", "raw-visit-id", "garbage"],
)
def test_invalid_pass_is_rejected_uniformly_without_side_effects(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    settings: Settings,
    db: Session,
    caplog: pytest.LogCaptureFixture,
    make_code: Callable[[Settings, str], str],
) -> None:
    visit = create_visit()
    code = make_code(settings, visit["id"])

    with caplog.at_level(logging.INFO):
        response = client.post(
            LOOKUP_URL, json={"code": code}, headers=auth_headers(users["security"])
        )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "VISITOR_PASS_INVALID"
    assert error["message"] == (
        "This visitor pass is not valid. Find the visitor in today's list instead."
    )
    assert visit["id"] not in response.text
    assert "Request rejected" in caplog.messages
    assert code not in caplog.text
    assert audit_count(db) == 1
    current = client.get(f"{VISITS_URL}/{visit['id']}", headers=auth_headers(users["admin"]))
    assert current.json()["status"] == "EXPECTED"


@pytest.mark.parametrize(
    ("body", "field"),
    [
        pytest.param({}, "code", id="missing"),
        pytest.param({"code": "   "}, "code", id="blank"),
        pytest.param({"code": "A" * 101}, "code", id="too-long"),
        pytest.param({"code": 123}, "code", id="not-a-string"),
        pytest.param({"code": "VP1-X", "visit_id": str(uuid.uuid4())}, "visit_id", id="extra"),
    ],
)
def test_malformed_lookup_request_is_a_validation_error(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    body: dict[str, Any],
    field: str,
) -> None:
    response = client.post(LOOKUP_URL, json=body, headers=auth_headers(users["security"]))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in {detail["field"] for detail in error["details"]}
    assert "A" * 101 not in response.text


def test_scan_does_not_bypass_check_in_permissions(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    # The registrant holds the pass, but only the front desk may resolve it or check in.
    visit = create_visit()
    code = get_pass(client, auth_headers, users["employee"], visit["id"])["code"]
    own = auth_headers(users["employee"])

    lookup = client.post(LOOKUP_URL, json={"code": code}, headers=own)
    check_in = client.post(f"{VISITS_URL}/{visit['id']}/check-in", headers=own)

    assert lookup.status_code == check_in.status_code == 403
