from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.domain.enums import Role
from app.main import create_app
from app.models import Base, User

TEST_PASSWORD = "Correct-Horse-42!"
# 09:30 UTC = 10:30 in Europe/Paris on 2026-10-28.
FIXED_NOW = datetime(2026, 10, 28, 9, 30, tzinfo=UTC)
TODAY = date(2026, 10, 28)
TOMORROW = TODAY + timedelta(days=1)

AuthHeaders = Callable[[User], dict[str, str]]
VisitFactory = Callable[..., dict[str, Any]]


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


@pytest.fixture(scope="session")
def password_hash() -> str:
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        jwt_secret_key="test-secret-key-that-is-long-enough-1234567890",
        environment="test",
        site_timezone="Europe/Paris",
        login_rate_limit_attempts=3,
        login_rate_limit_window_seconds=60,
        log_level="WARNING",
    )


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(FIXED_NOW)


@pytest.fixture
def app(settings: Settings, clock: FixedClock) -> Iterator[FastAPI]:
    application = create_app(settings, clock)
    Base.metadata.create_all(application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def users(db: Session, password_hash: str) -> dict[str, User]:
    specs = {
        "employee": ("alice@acme-corp.com", "Alice Employee", Role.EMPLOYEE, True),
        "other_employee": ("bob@acme-corp.com", "Bob Employee", Role.EMPLOYEE, True),
        "security": ("sam@acme-corp.com", "Sam Security", Role.SECURITY, True),
        "admin": ("ada@acme-corp.com", "Ada Admin", Role.ADMIN, True),
        "inactive": ("ivan@acme-corp.com", "Ivan Inactive", Role.EMPLOYEE, False),
    }
    created = {
        key: User(
            email=email,
            full_name=name,
            role=role,
            is_active=active,
            password_hash=password_hash,
        )
        for key, (email, name, role, active) in specs.items()
    }
    db.add_all(created.values())
    db.commit()
    return created


@pytest.fixture
def auth_headers(settings: Settings) -> AuthHeaders:
    def build(user: User) -> dict[str, str]:
        token = create_access_token(user.id, user.role, settings)
        return {"Authorization": f"Bearer {token.value}"}

    return build


def visit_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "visitor": {
            "full_name": "Jane Doe",
            "email": "Jane.Doe@Contoso.com",
            "phone": "+33 6 12 34 56 78",
            "company": "Contoso",
        },
        "purpose": "Quarterly review",
        "expected_date": TODAY.isoformat(),
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def create_visit(
    client: TestClient, users: dict[str, User], auth_headers: AuthHeaders
) -> VisitFactory:
    def create(as_user: str = "employee", **overrides: Any) -> dict[str, Any]:
        response = client.post(
            "/api/v1/visits", json=visit_payload(**overrides), headers=auth_headers(users[as_user])
        )
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    return create
