import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings
from app.domain.enums import Role
from app.domain.errors import AuthenticationError, ErrorCode

BCRYPT_MAX_PASSWORD_BYTES = 72
_TOKEN_TYPE = "access"  # noqa: S105 - JWT type claim, not a secret

# Used to keep login timing constant when the email is unknown (prevents user enumeration).
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt()).decode()


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str
    expires_in_seconds: int


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: uuid.UUID
    role: Role


def hash_password(password: str) -> str:
    encoded = password.encode()
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode()
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode())


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: uuid.UUID, role: Role, settings: Settings) -> AccessToken:
    issued_at = datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "typ": _TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return AccessToken(value=token, expires_in_seconds=int(lifetime.total_seconds()))


def decode_access_token(token: str, settings: Settings) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "role", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(
            "Your session has expired. Please sign in again.", code=ErrorCode.AUTH_TOKEN_EXPIRED
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise _invalid_token() from exc

    if payload.get("typ") != _TOKEN_TYPE:
        raise _invalid_token()
    try:
        return TokenClaims(user_id=uuid.UUID(str(payload["sub"])), role=Role(payload["role"]))
    except ValueError as exc:
        raise _invalid_token() from exc


def _invalid_token() -> AuthenticationError:
    return AuthenticationError("Invalid authentication token.", code=ErrorCode.AUTH_TOKEN_INVALID)
