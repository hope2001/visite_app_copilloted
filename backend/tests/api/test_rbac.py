"""Route x role matrix: every endpoint is checked for every role (deny by default)."""

import base64
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token
from app.domain.enums import Role
from app.models import AuditLog, User
from tests.conftest import AuthHeaders, VisitFactory, visit_payload

ROLES = ("employee", "security", "admin")
ANY_ID = "00000000-0000-4000-8000-000000000000"

# (method, path, roles allowed past RBAC)
ROUTES = [
    ("GET", "/api/v1/auth/me", {"employee", "security", "admin"}),
    ("GET", "/api/v1/users/hosts", {"employee", "admin"}),
    ("POST", "/api/v1/visits", {"employee", "admin"}),
    ("GET", "/api/v1/visits", {"employee", "admin"}),
    ("GET", "/api/v1/visits/today", {"security", "admin"}),
    ("GET", "/api/v1/visits/{id}", {"employee", "security", "admin"}),
    ("POST", "/api/v1/visits/{id}/check-in", {"security", "admin"}),
    ("POST", "/api/v1/visits/{id}/check-out", {"security", "admin"}),
    ("POST", "/api/v1/visits/{id}/cancel", {"employee", "admin"}),
    ("GET", "/api/v1/visits/{id}/audit", {"security", "admin"}),
    ("GET", "/api/v1/visits/{id}/pass", {"employee", "admin"}),
    ("POST", "/api/v1/visits/pass-lookup", {"security", "admin"}),
    ("GET", "/api/v1/audit-logs", {"admin"}),
]


@pytest.mark.parametrize(("method", "path", "allowed"), ROUTES)
def test_unauthenticated_requests_are_rejected(
    client: TestClient, method: str, path: str, allowed: set[str]
) -> None:
    response = client.request(method, path.format(id=ANY_ID))
    assert response.status_code == 401


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(("method", "path", "allowed"), ROUTES)
def test_role_matrix(
    client: TestClient,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    method: str,
    path: str,
    allowed: set[str],
    role: str,
) -> None:
    body = visit_payload() if path == "/api/v1/visits" and method == "POST" else None
    response = client.request(
        method,
        path.format(id=uuid.uuid4()),
        json=body,
        headers=auth_headers(users[role]),
    )

    if role in allowed:
        assert response.status_code != 403, response.text
    else:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_security_cannot_see_employee_listing_data(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
) -> None:
    create_visit()
    response = client.get("/api/v1/visits", headers=auth_headers(users["security"]))
    assert response.status_code == 403


# ---- Unauthorized access: forged, expired and stale credentials -----------------------------


def _signed(settings: Settings, key: str | None = None, **overrides: Any) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": ANY_ID,
        "role": "ADMIN",
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    } | overrides
    return jwt.encode(claims, key or settings.jwt_secret_key, algorithm="HS256")


def _unsigned(user_id: uuid.UUID) -> str:
    def part(data: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    exp = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    claims = {"sub": str(user_id), "role": "ADMIN", "typ": "access", "iat": exp - 300, "exp": exp}
    return f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims)}."


Authorization = Callable[[Settings, dict[str, User]], str]


def _expired(settings: Settings, users: dict[str, User]) -> str:
    past = datetime.now(UTC) - timedelta(seconds=1)
    return "Bearer " + _signed(settings, sub=str(users["security"].id), exp=past)


BAD_CREDENTIALS: list[Any] = [
    pytest.param(_expired, "AUTH_TOKEN_EXPIRED", id="expired"),
    pytest.param(
        lambda s, u: "Bearer " + _signed(s, key="x" * 64, sub=str(u["security"].id)),
        "AUTH_TOKEN_INVALID",
        id="wrong-signing-key",
    ),
    pytest.param(
        lambda s, u: "Bearer " + _unsigned(u["security"].id),
        "AUTH_TOKEN_INVALID",
        id="alg-none",
    ),
    pytest.param(
        lambda s, u: "Bearer " + _signed(s, sub=str(uuid.uuid4())),
        "AUTH_TOKEN_INVALID",
        id="unknown-user",
    ),
    pytest.param(
        lambda s, u: "Bearer " + _signed(s, sub=str(u["security"].id), typ="refresh"),
        "AUTH_TOKEN_INVALID",
        id="wrong-token-type",
    ),
    pytest.param(
        lambda s, u: "Bearer " + create_access_token(u["inactive"].id, Role.ADMIN, s).value,
        "AUTH_TOKEN_INVALID",
        id="inactive-user",
    ),
    pytest.param(lambda s, u: "Bearer not-a-jwt", "AUTH_TOKEN_INVALID", id="garbage"),
    pytest.param(
        lambda s, u: "Basic " + create_access_token(u["security"].id, Role.SECURITY, s).value,
        None,
        id="wrong-scheme",
    ),
]


@pytest.mark.parametrize(("authorization", "code"), BAD_CREDENTIALS)
def test_bad_credentials_cannot_check_in_a_visitor(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    settings: Settings,
    db: Session,
    authorization: Authorization,
    code: str | None,
) -> None:
    visit = create_visit()

    response = client.post(
        f"/api/v1/visits/{visit['id']}/check-in",
        headers={"Authorization": authorization(settings, users)},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")
    if code is not None:
        assert response.json()["error"]["code"] == code
    current = client.get(f"/api/v1/visits/{visit['id']}", headers=auth_headers(users["admin"]))
    assert current.json()["status"] == "EXPECTED"
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


@pytest.mark.parametrize("path", ["/api/v1/audit-logs", "/api/v1/visits/today"])
def test_role_claim_in_token_cannot_escalate_privileges(
    client: TestClient, users: dict[str, User], settings: Settings, path: str
) -> None:
    # Validly signed token for an employee that claims ADMIN: the database role wins.
    token = create_access_token(users["employee"].id, Role.ADMIN, settings).value

    response = client.get(path, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_demoted_admin_loses_access_immediately(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders, db: Session
) -> None:
    headers = auth_headers(users["admin"])
    assert client.get("/api/v1/audit-logs", headers=headers).status_code == 200

    users["admin"].role = Role.EMPLOYEE
    db.commit()

    assert client.get("/api/v1/audit-logs", headers=headers).status_code == 403


def test_deactivated_operator_token_stops_working_immediately(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
) -> None:
    visit = create_visit()
    headers = auth_headers(users["security"])

    users["security"].is_active = False
    db.commit()
    response = client.post(f"/api/v1/visits/{visit['id']}/check-in", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_INVALID"
    current = client.get(f"/api/v1/visits/{visit['id']}", headers=auth_headers(users["admin"]))
    assert current.json()["status"] == "EXPECTED"


@pytest.mark.parametrize(
    ("role", "action"),
    [("employee", "check-in"), ("employee", "check-out"), ("security", "cancel")],
)
def test_wrong_role_cannot_change_visit_status(
    client: TestClient,
    create_visit: VisitFactory,
    users: dict[str, User],
    auth_headers: AuthHeaders,
    db: Session,
    role: str,
    action: str,
) -> None:
    # The employee is the registrant and host of this visit, yet cannot act as front desk.
    visit = create_visit()

    response = client.post(
        f"/api/v1/visits/{visit['id']}/{action}", headers=auth_headers(users[role])
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    current = client.get(f"/api/v1/visits/{visit['id']}", headers=auth_headers(users["admin"]))
    assert current.json() == visit
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1
