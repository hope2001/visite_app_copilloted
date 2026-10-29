from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.error_handlers import GENERIC_INTERNAL_ERROR_MESSAGE
from app.schemas.common import ErrorResponse


class _DriverError(Exception):
    pass


@pytest.fixture
def failing_client(app: FastAPI) -> Iterator[TestClient]:
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    def duplicate() -> None:
        raise IntegrityError("INSERT ...", {}, _DriverError("UNIQUE constraint failed"))

    def locked() -> None:
        raise OperationalError("UPDATE ...", {}, _DriverError("database is locked"))

    app.add_api_route("/test/boom", boom)
    app.add_api_route("/test/duplicate", duplicate)
    app.add_api_route("/test/locked", locked)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_unexpected_error_hides_internals(failing_client: TestClient) -> None:
    response = failing_client.get("/test/boom")

    assert response.status_code == 500
    error = ErrorResponse.model_validate(response.json()).error
    assert error.code == "INTERNAL_ERROR"
    assert error.message == GENERIC_INTERNAL_ERROR_MESSAGE
    assert error.request_id
    assert "secret" not in response.text
    assert "Traceback" not in response.text


def test_integrity_error_maps_to_conflict(failing_client: TestClient) -> None:
    response = failing_client.get("/test/duplicate")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert "UNIQUE" not in response.text


def test_locked_database_maps_to_503_with_retry(failing_client: TestClient) -> None:
    response = failing_client.get("/test/locked")
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert ErrorResponse.model_validate(response.json()).error.code == "NOT_FOUND"


def test_method_not_allowed_uses_error_envelope(client: TestClient) -> None:
    response = client.delete("/api/v1/visits/today")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_request_id_is_echoed_when_safe(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc-12345678"})
    assert response.headers["X-Request-ID"] == "abc-12345678"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "bad\nvalue injected"})
    assert response.headers["X-Request-ID"] != "bad\nvalue injected"
    assert len(response.headers["X-Request-ID"]) == 32


def test_error_request_id_matches_header(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
