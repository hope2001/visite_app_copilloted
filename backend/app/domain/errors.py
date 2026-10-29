"""Domain errors. Services raise these; the API layer maps them to HTTP responses."""

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"  # noqa: S105 - error code, not a secret
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"  # noqa: S105 - error code, not a secret
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VISIT_NOT_FOUND = "VISIT_NOT_FOUND"
    HOST_NOT_FOUND = "HOST_NOT_FOUND"
    VISIT_INVALID_TRANSITION = "VISIT_INVALID_TRANSITION"
    VISIT_NOT_DUE_TODAY = "VISIT_NOT_DUE_TODAY"
    VISITOR_PASS_INVALID = "VISITOR_PASS_INVALID"  # noqa: S105 - error code, not a secret
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class FieldIssue:
    field: str
    issue: str


class AppError(Exception):
    default_code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        details: tuple[FieldIssue, ...] = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details


class AuthenticationError(AppError):
    default_code = ErrorCode.AUTH_INVALID_CREDENTIALS


class PermissionDeniedError(AppError):
    default_code = ErrorCode.FORBIDDEN


class NotFoundError(AppError):
    default_code = ErrorCode.NOT_FOUND


class InvalidStateTransitionError(AppError):
    default_code = ErrorCode.VISIT_INVALID_TRANSITION


class ConflictError(AppError):
    default_code = ErrorCode.CONFLICT


class BusinessRuleError(AppError):
    default_code = ErrorCode.VALIDATION_ERROR


class RateLimitedError(AppError):
    default_code = ErrorCode.RATE_LIMITED

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
