"""Translate exceptions into the standard error envelope. No internals reach the client."""

import logging
from collections.abc import Iterable, Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import REQUEST_ID_HEADER
from app.domain.errors import (
    AppError,
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    ErrorCode,
    FieldIssue,
    InvalidStateTransitionError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
)
from app.schemas.common import ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger("app.errors")

_STATUS_BY_ERROR: Mapping[type[AppError], int] = {
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidStateTransitionError: status.HTTP_409_CONFLICT,
    ConflictError: status.HTTP_409_CONFLICT,
    BusinessRuleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RateLimitedError: status.HTTP_429_TOO_MANY_REQUESTS,
}

_CODE_BY_HTTP_STATUS: Mapping[int, ErrorCode] = {
    status.HTTP_401_UNAUTHORIZED: ErrorCode.AUTH_TOKEN_INVALID,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
}

_LOCATION_PREFIXES = frozenset({"body", "query", "path", "header", "cookie"})

GENERIC_INTERNAL_ERROR_MESSAGE = "An unexpected error occurred. Please try again later."


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, _handle_integrity_error)  # type: ignore[arg-type]
    app.add_exception_handler(OperationalError, _handle_operational_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)


def error_response(
    request: Request,
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    details: Iterable[ErrorDetail] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=list(details), request_id=request_id)
    )
    response_headers = dict(headers or {})
    if request_id:
        response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=response_headers
    )


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    status_code = _status_for(exc)
    logger.warning(
        "Request rejected",
        extra={"code": exc.code.value, "status": status_code, "path": request.url.path},
    )
    return error_response(
        request,
        status_code=status_code,
        code=exc.code,
        message=exc.message,
        details=_to_error_details(exc.details),
        headers=_headers_for(exc),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(field=_field_path(error.get("loc", ())), issue=str(error.get("msg", "")))
        for error in exc.errors()
    ]
    return error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code=ErrorCode.VALIDATION_ERROR,
        message="The request contains invalid data.",
        details=details,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _CODE_BY_HTTP_STATUS.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=dict(exc.headers) if exc.headers else None,
    )


async def _handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity constraint violated", extra={"path": request.url.path})
    return error_response(
        request,
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.CONFLICT,
        message="The request conflicts with existing data. Refresh and try again.",
    )


async def _handle_operational_error(request: Request, exc: OperationalError) -> JSONResponse:
    if "locked" in str(exc.orig).lower():
        logger.warning("Database busy", extra={"path": request.url.path})
        return error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="The service is busy. Please retry in a moment.",
            headers={"Retry-After": "1"},
        )
    return await _handle_unexpected_error(request, exc)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", extra={"path": request.url.path}, exc_info=exc)
    return error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message=GENERIC_INTERNAL_ERROR_MESSAGE,
    )


def _status_for(exc: AppError) -> int:
    for error_type in type(exc).__mro__:
        if error_type in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[error_type]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _headers_for(exc: AppError) -> dict[str, str] | None:
    if isinstance(exc, AuthenticationError):
        return {"WWW-Authenticate": "Bearer"}
    if isinstance(exc, RateLimitedError):
        return {"Retry-After": str(exc.retry_after_seconds)}
    return None


def _to_error_details(issues: Iterable[FieldIssue]) -> list[ErrorDetail]:
    return [ErrorDetail(field=issue.field, issue=issue.issue) for issue in issues]


def _field_path(location: Iterable[object]) -> str | None:
    parts = [str(part) for part in location]
    if parts and parts[0] in _LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(parts) or None
