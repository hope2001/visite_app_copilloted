import uuid

import pytest

from app.domain.enums import Role
from app.domain.policies import can_cancel_visit, can_view_visit
from app.models import User, Visit


def make_user(role: Role) -> User:
    return User(id=uuid.uuid4(), role=role)


def make_visit(registered_by: User, host: User) -> Visit:
    return Visit(id=uuid.uuid4(), registered_by_id=registered_by.id, host_id=host.id)


@pytest.fixture
def registrant() -> User:
    return make_user(Role.EMPLOYEE)


@pytest.fixture
def host() -> User:
    return make_user(Role.EMPLOYEE)


@pytest.fixture
def visit(registrant: User, host: User) -> Visit:
    return make_visit(registrant, host)


def test_registrant_and_host_can_view(registrant: User, host: User, visit: Visit) -> None:
    assert can_view_visit(registrant, visit)
    assert can_view_visit(host, visit)


def test_unrelated_employee_cannot_view(visit: Visit) -> None:
    assert not can_view_visit(make_user(Role.EMPLOYEE), visit)


@pytest.mark.parametrize("role", [Role.SECURITY, Role.ADMIN])
def test_front_desk_roles_can_view_any_visit(role: Role, visit: Visit) -> None:
    assert can_view_visit(make_user(role), visit)


def test_only_registrant_or_admin_can_cancel(registrant: User, host: User, visit: Visit) -> None:
    assert can_cancel_visit(registrant, visit)
    assert can_cancel_visit(make_user(Role.ADMIN), visit)
    assert not can_cancel_visit(host, visit)
    assert not can_cancel_visit(make_user(Role.SECURITY), visit)
