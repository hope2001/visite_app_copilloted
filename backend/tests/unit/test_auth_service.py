"""Security tests for login throttling (H1: brute force via rotating client addresses)."""

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.rate_limit import FailedAttemptLimiter
from app.domain.errors import AuthenticationError, RateLimitedError
from app.models import User
from app.services.auth_service import AuthService
from tests.conftest import TEST_PASSWORD

EMAIL = "alice@acme-corp.com"


def build_service(db: Session, settings: Settings, account_attempts: int) -> AuthService:
    clock = lambda: 1_000.0  # noqa: E731 - frozen time: nothing expires during the test
    return AuthService(
        db,
        settings,
        FailedAttemptLimiter(max_attempts=3, window_seconds=60, monotonic=clock),
        FailedAttemptLimiter(max_attempts=account_attempts, window_seconds=60, monotonic=clock),
    )


def test_rotating_client_addresses_cannot_bypass_account_lockout(
    db: Session, settings: Settings, users: dict[str, User]
) -> None:
    service = build_service(db, settings, account_attempts=5)

    for attempt in range(5):
        with pytest.raises(AuthenticationError):
            service.login(EMAIL, "wrong-guess", client_address=f"203.0.113.{attempt}")

    # Even the correct password from a fresh address is refused while the account is locked.
    with pytest.raises(RateLimitedError):
        service.login(EMAIL, TEST_PASSWORD, client_address="198.51.100.77")


def test_account_lockout_is_case_and_whitespace_insensitive(
    db: Session, settings: Settings, users: dict[str, User]
) -> None:
    service = build_service(db, settings, account_attempts=2)

    for variant in (" ALICE@acme-corp.com", "Alice@Acme-Corp.com "):
        with pytest.raises(AuthenticationError):
            service.login(variant, "wrong-guess", client_address="203.0.113.1")
    with pytest.raises(RateLimitedError):
        service.login(EMAIL, TEST_PASSWORD, client_address="203.0.113.2")


def test_account_lockout_does_not_affect_other_accounts(
    db: Session, settings: Settings, users: dict[str, User]
) -> None:
    service = build_service(db, settings, account_attempts=2)
    for attempt in range(2):
        with pytest.raises(AuthenticationError):
            service.login(EMAIL, "wrong-guess", client_address=f"203.0.113.{attempt}")

    token = service.login("bob@acme-corp.com", TEST_PASSWORD, client_address="203.0.113.9")

    assert token.value


def test_per_client_limit_still_applies_below_account_limit(
    db: Session, settings: Settings, users: dict[str, User]
) -> None:
    service = build_service(db, settings, account_attempts=50)
    for _ in range(3):
        with pytest.raises(AuthenticationError):
            service.login(EMAIL, "wrong-guess", client_address="203.0.113.1")

    with pytest.raises(RateLimitedError):
        service.login(EMAIL, TEST_PASSWORD, client_address="203.0.113.1")
    # A different client is not blocked by the per-client limit.
    assert service.login(EMAIL, TEST_PASSWORD, client_address="198.51.100.1").value


def test_app_wires_account_limiter_from_settings(settings: Settings) -> None:
    from app.main import create_app

    app = create_app(settings)
    try:
        limiter = app.state.account_login_limiter
        assert isinstance(limiter, FailedAttemptLimiter)
        assert limiter is not app.state.login_limiter
    finally:
        app.state.engine.dispose()
