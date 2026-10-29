import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, User, Visitor
from tests.conftest import (
    TODAY,
    TOMORROW,
    AuthHeaders,
    FixedClock,
    VisitFactory,
    visit_payload,
)

VISITS_URL = "/api/v1/visits"


def audit_actions(db: Session, visit_id: str) -> list[str]:
    """Recorded actions, sorted: the fixed test clock can give rows identical timestamps."""
    rows = db.scalars(select(AuditLog.action).where(AuditLog.visit_id == uuid.UUID(visit_id)))
    return sorted(action.value for action in rows)


# ---- Registration ---------------------------------------------------------------------------


def test_register_visit_defaults_host_to_registrant_and_audits(
    create_visit: VisitFactory, users: dict[str, User], db: Session
) -> None:
    visit = create_visit()

    assert visit["status"] == "EXPECTED"
    assert visit["host"]["id"] == str(users["employee"].id)
    assert visit["registered_by"]["id"] == str(users["employee"].id)
    assert visit["visitor"]["email"] == "jane.doe@contoso.com"
    uuid.UUID(visit["id"])
    assert audit_actions(db, visit["id"]) == ["VISIT_CREATED"]


def test_register_visit_for_another_host(
    create_visit: VisitFactory, users: dict[str, User]
) -> None:
    visit = create_visit(host_id=str(users["other_employee"].id))
    assert visit["host"]["id"] == str(users["other_employee"].id)


def test_returning_visitor_is_reused_and_updated(create_visit: VisitFactory, db: Session) -> None:
    create_visit()
    payload = visit_payload()["visitor"] | {"company": "Contoso Ltd", "phone": ""}
    second = create_visit(visitor=payload, expected_date=TOMORROW.isoformat())

    assert db.scalar(select(func.count()).select_from(Visitor)) == 1
    assert second["visitor"]["company"] == "Contoso Ltd"
    assert second["visitor"]["phone"] is None


# ---- Security: visitor identity cannot be altered through another registration (H2) -------


def test_other_employee_cannot_rewrite_identity_shown_for_existing_visit(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    original = create_visit()
    tampered = visit_payload()["visitor"] | {
        "full_name": "Mallory Impostor",
        "company": "Evil Corp",
        "phone": "+1 555 0000",
    }
    create_visit(as_user="other_employee", visitor=tampered, expected_date=TOMORROW.isoformat())

    owner_view = client.get(
        f"{VISITS_URL}/{original['id']}", headers=auth_headers(users["employee"])
    ).json()
    security_today = client.get(
        f"{VISITS_URL}/today", headers=auth_headers(users["security"])
    ).json()

    for visit in (owner_view, *security_today):
        assert visit["visitor"]["full_name"] == "Jane Doe"
        assert visit["visitor"]["company"] == "Contoso"
        assert visit["visitor"]["phone"] == "+33 6 12 34 56 78"
        assert visit["visitor"]["id"] == original["visitor"]["id"]


def test_visit_search_matches_details_registered_for_that_visit(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    original = create_visit()
    renamed = visit_payload()["visitor"] | {"full_name": "Mallory Impostor"}
    create_visit(as_user="other_employee", visitor=renamed, expected_date=TOMORROW.isoformat())
    headers = auth_headers(users["security"])

    by_original = client.get(f"{VISITS_URL}/today", params={"q": "jane"}, headers=headers).json()
    by_new_name = client.get(f"{VISITS_URL}/today", params={"q": "mallory"}, headers=headers).json()

    assert [v["id"] for v in by_original] == [original["id"]]
    assert by_new_name == []


def test_past_date_is_rejected_with_field_detail(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> None:
    response = client.post(
        VISITS_URL,
        json=visit_payload(expected_date="2026-10-27"),
        headers=auth_headers(users["employee"]),
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "expected_date"


def test_security_or_inactive_host_is_rejected(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> None:
    for host in ("security", "inactive"):
        response = client.post(
            VISITS_URL,
            json=visit_payload(host_id=str(users[host].id)),
            headers=auth_headers(users["employee"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "HOST_NOT_FOUND"


def test_invalid_input_lists_every_field_issue(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> None:
    payload = visit_payload(purpose="", status="CHECKED_IN")
    payload["visitor"] |= {"email": "not-an-email", "phone": "abc"}

    response = client.post(VISITS_URL, json=payload, headers=auth_headers(users["employee"]))

    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    assert {"purpose", "status", "visitor.email", "visitor.phone"} <= fields


# ---- Reading & scoping ----------------------------------------------------------------------


def test_employee_sees_registered_and_hosted_visits_only(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    mine = create_visit()
    hosted_for_me = create_visit(as_user="other_employee", host_id=str(users["employee"].id))
    create_visit(as_user="other_employee")

    response = client.get(VISITS_URL, headers=auth_headers(users["employee"]))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {mine["id"], hosted_for_me["id"]}


def test_admin_sees_all_visits_with_filters_and_paging(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    create_visit()
    create_visit(as_user="other_employee", expected_date=TOMORROW.isoformat())
    headers = auth_headers(users["admin"])

    all_visits = client.get(VISITS_URL, params={"size": 1}, headers=headers).json()
    tomorrow_only = client.get(
        VISITS_URL, params={"date_from": TOMORROW.isoformat()}, headers=headers
    ).json()

    assert all_visits["total"] == 2
    assert len(all_visits["items"]) == 1
    assert tomorrow_only["total"] == 1


def test_search_wildcards_are_treated_literally(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    create_visit()
    response = client.get(VISITS_URL, params={"q": "%"}, headers=auth_headers(users["admin"]))
    assert response.json()["total"] == 0


def test_invalid_date_range_is_rejected(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> None:
    response = client.get(
        VISITS_URL,
        params={"date_from": "2026-11-02", "date_to": "2026-11-01"},
        headers=auth_headers(users["admin"]),
    )
    assert response.status_code == 422


def test_other_employee_gets_404_for_visit_they_cannot_see(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit()
    response = client.get(
        f"{VISITS_URL}/{visit['id']}", headers=auth_headers(users["other_employee"])
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VISIT_NOT_FOUND"


def test_malformed_and_unknown_ids(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> None:
    headers = auth_headers(users["admin"])

    malformed = client.get(f"{VISITS_URL}/not-a-uuid", headers=headers)
    unknown = client.get(f"{VISITS_URL}/{uuid.uuid4()}", headers=headers)

    assert malformed.status_code == 422
    assert malformed.json()["error"]["details"][0]["field"] == "visit_id"
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "VISIT_NOT_FOUND"


def test_today_list_is_sorted_and_searchable(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    headers = auth_headers(users["security"])
    zed = create_visit(visitor=visit_payload()["visitor"] | {"full_name": "Zed", "email": "z@x.io"})
    create_visit(visitor=visit_payload()["visitor"] | {"full_name": "Amy", "email": "a@x.io"})
    create_visit(expected_date=TOMORROW.isoformat())
    client.post(f"{VISITS_URL}/{zed['id']}/check-in", headers=headers)

    today = client.get(f"{VISITS_URL}/today", headers=headers).json()
    searched = client.get(f"{VISITS_URL}/today", params={"q": "ze"}, headers=headers).json()

    assert [(v["visitor"]["full_name"], v["status"]) for v in today] == [
        ("Amy", "EXPECTED"),
        ("Zed", "CHECKED_IN"),
    ]
    assert [v["visitor"]["full_name"] for v in searched] == ["Zed"]


# ---- Lifecycle ------------------------------------------------------------------------------


def test_full_lifecycle_is_audited(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    clock: FixedClock,
    db: Session,
) -> None:
    visit = create_visit()
    headers = auth_headers(users["security"])

    clock.advance(timedelta(minutes=5))
    checked_in = client.post(f"{VISITS_URL}/{visit['id']}/check-in", headers=headers)
    clock.advance(timedelta(hours=2))
    checked_out = client.post(f"{VISITS_URL}/{visit['id']}/check-out", headers=headers)
    trail = client.get(f"{VISITS_URL}/{visit['id']}/audit", headers=headers)

    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "CHECKED_IN"
    assert checked_in.json()["checked_in_at"] is not None
    assert checked_out.json()["status"] == "CHECKED_OUT"
    assert [entry["action"] for entry in trail.json()] == [
        "VISIT_CREATED",
        "CHECKED_IN",
        "CHECKED_OUT",
    ]
    check_in_entry: dict[str, Any] = trail.json()[1]
    assert check_in_entry["performed_by"]["id"] == str(users["security"].id)
    assert (check_in_entry["from_status"], check_in_entry["to_status"]) == (
        "EXPECTED",
        "CHECKED_IN",
    )


def test_double_check_in_is_rejected_without_extra_audit(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
) -> None:
    visit = create_visit()
    headers = auth_headers(users["security"])
    client.post(f"{VISITS_URL}/{visit['id']}/check-in", headers=headers)

    second = client.post(f"{VISITS_URL}/{visit['id']}/check-in", headers=headers)

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "VISIT_INVALID_TRANSITION"
    assert audit_actions(db, visit["id"]) == ["CHECKED_IN", "VISIT_CREATED"]


def test_check_out_requires_check_in(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit()
    response = client.post(
        f"{VISITS_URL}/{visit['id']}/check-out", headers=auth_headers(users["security"])
    )
    assert response.status_code == 409


def test_check_in_only_on_expected_date(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
) -> None:
    visit = create_visit(expected_date=TOMORROW.isoformat())
    response = client.post(
        f"{VISITS_URL}/{visit['id']}/check-in", headers=auth_headers(users["security"])
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VISIT_NOT_DUE_TODAY"
    assert audit_actions(db, visit["id"]) == ["VISIT_CREATED"]


def test_cancel_rules(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    visit = create_visit(host_id=str(users["other_employee"].id))
    url = f"{VISITS_URL}/{visit['id']}/cancel"

    by_host = client.post(url, headers=auth_headers(users["other_employee"]))
    by_registrant = client.post(url, headers=auth_headers(users["employee"]))
    again = client.post(url, headers=auth_headers(users["employee"]))

    assert by_host.status_code == 403
    assert by_registrant.status_code == 200
    assert by_registrant.json()["status"] == "CANCELLED"
    assert again.status_code == 409


def test_today_is_computed_in_site_timezone(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    clock: FixedClock,
) -> None:
    visit = create_visit()
    # 23:30 UTC on the 28th is already the 29th in Paris.
    clock.set(datetime(TODAY.year, TODAY.month, TODAY.day, 23, 30, tzinfo=UTC))

    response = client.post(
        f"{VISITS_URL}/{visit['id']}/check-in", headers=auth_headers(users["security"])
    )
    assert response.json()["error"]["code"] == "VISIT_NOT_DUE_TODAY"
