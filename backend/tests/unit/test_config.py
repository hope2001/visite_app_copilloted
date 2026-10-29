"""Security tests for secret configuration (H3: placeholder / weak JWT secrets)."""

import secrets
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]

# The values that used to ship in the .env.example files: copying them must not boot the app.
FORMER_EXAMPLE_SECRETS = (
    "replace-with-a-long-random-secret-of-at-least-32-chars",
    "change-me-to-a-long-random-secret-of-at-least-32-chars",
)


def build(secret: str) -> Settings:
    return Settings(jwt_secret_key=secret, environment="test", _env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "secret",
    [
        *FORMER_EXAMPLE_SECRETS,
        "CHANGEME-" + secrets.token_urlsafe(32),
        secrets.token_urlsafe(32) + "-your-secret",
        "replace-me-" + secrets.token_urlsafe(32),
    ],
)
def test_placeholder_secrets_are_rejected(secret: str) -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        build(secret)


@pytest.mark.parametrize("secret", ["a" * 64, "abab" * 16, "012345678" * 4])
def test_low_entropy_secrets_are_rejected(secret: str) -> None:
    with pytest.raises(ValidationError, match="predictable"):
        build(secret)


def test_short_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build(secrets.token_urlsafe(16)[:31])


def test_random_secret_is_accepted() -> None:
    secret = secrets.token_urlsafe(48)
    assert build(secret).jwt_secret_key == secret


@pytest.mark.parametrize("secret", [*FORMER_EXAMPLE_SECRETS, "x" * 40, "short-secret"])
def test_rejected_secret_is_not_echoed_in_validation_error(secret: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        build(secret)

    assert secret not in str(excinfo.value)


@pytest.mark.parametrize("path", [".env.example", "backend/.env.example"])
def test_env_examples_ship_no_usable_secrets(path: str) -> None:
    values = dict(
        line.split("=", 1)
        for line in (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )

    assert values["VMP_JWT_SECRET_KEY"] == ""
    assert values["VMP_SEED_PASSWORD"] == ""
