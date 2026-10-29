from enum import StrEnum


class Role(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"


class VisitStatus(StrEnum):
    EXPECTED = "EXPECTED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"


class AuditAction(StrEnum):
    VISIT_CREATED = "VISIT_CREATED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"


HOST_ROLES = frozenset({Role.EMPLOYEE, Role.ADMIN})
FRONT_DESK_ROLES = frozenset({Role.SECURITY, Role.ADMIN})
