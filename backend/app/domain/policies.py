"""Object-level access rules. Kept in one place so routers and services never duplicate them."""

from sqlalchemy import Select, false, or_

from app.domain.enums import FRONT_DESK_ROLES, Role
from app.models import User, Visit


def can_view_visit(user: User, visit: Visit) -> bool:
    if user.role in FRONT_DESK_ROLES:
        return True
    return user.id in (visit.registered_by_id, visit.host_id)


def can_cancel_visit(user: User, visit: Visit) -> bool:
    return user.role == Role.ADMIN or user.id == visit.registered_by_id


def scope_visit_query[T: tuple[object, ...]](user: User, statement: Select[T]) -> Select[T]:
    """Restrict a visit listing to what the user may see (deny by default)."""
    if user.role == Role.ADMIN:
        return statement
    if user.role == Role.EMPLOYEE:
        return statement.where(or_(Visit.registered_by_id == user.id, Visit.host_id == user.id))
    return statement.where(false())
