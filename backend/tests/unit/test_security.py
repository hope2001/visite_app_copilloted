import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.enums import Role
from app.domain.errors import AuthenticationError, ErrorCode


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_overlong_password_is_rejected_safely() -> None:
    with pytest.raises(ValueError, match="at most"):
        hash_password("x" * 73)
    assert not verify_password("x" * 73, hash_password("short-password"))


def test_token_roundtrip(settings: Settings) -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id, Role.SECURITY, settings)

    claims = decode_access_token(token.value, settings)

    assert claims.user_id == user_id
    assert claims.role == Role.SECURITY
    assert token.expires_in_seconds == settings.access_token_expire_minutes * 60


def _encode(settings: Settings, **overrides: object) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "role": "ADMIN",
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def test_expired_token_has_specific_code(settings: Settings) -> None:
    token = _encode(settings, exp=datetime.now(UTC) - timedelta(seconds=1))
    with pytest.raises(AuthenticationError) as error:
        decode_access_token(token, settings)
    assert error.value.code == ErrorCode.AUTH_TOKEN_EXPIRED


@pytest.mark.parametrize(
    "token_factory",
    [
        lambda s: _encode(s, typ="refresh"),
        lambda s: _encode(s, sub="not-a-uuid"),
        lambda s: _encode(s, role="SUPERUSER"),
        lambda s: jwt.encode({"sub": "x"}, "another-secret-key-that-is-long-enough!!", "HS256"),
        lambda s: "garbage",
    ],
    ids=["wrong-type", "bad-subject", "unknown-role", "bad-signature", "malformed"],
)
def test_invalid_tokens_are_rejected(settings: Settings, token_factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(AuthenticationError) as error:
        decode_access_token(token_factory(settings), settings)
    assert error.value.code == ErrorCode.AUTH_TOKEN_INVALID
