from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.rate_limit import FailedAttemptLimiter
from app.core.security import (
    AccessToken,
    burn_password_check,
    create_access_token,
    verify_password,
)
from app.domain.errors import AuthenticationError
from app.models import User


class AuthService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        client_limiter: FailedAttemptLimiter,
        account_limiter: FailedAttemptLimiter,
    ) -> None:
        self._db = db
        self._settings = settings
        self._client_limiter = client_limiter
        self._account_limiter = account_limiter

    def login(self, email: str, password: str, client_address: str) -> AccessToken:
        normalised_email = email.strip().lower()
        client_key = f"{client_address}:{normalised_email}"
        # The client address can be spoofed or rotated, so each account also has its own cap.
        self._client_limiter.ensure_allowed(client_key)
        self._account_limiter.ensure_allowed(normalised_email)

        user = self._find_active_user_with_password(normalised_email, password)
        if user is None:
            self._client_limiter.record_failure(client_key)
            self._account_limiter.record_failure(normalised_email)
            raise AuthenticationError("Invalid email or password.")

        self._client_limiter.reset(client_key)
        return create_access_token(user.id, user.role, self._settings)

    def _find_active_user_with_password(self, email: str, password: str) -> User | None:
        user = self._db.scalar(select(User).where(User.email == email))
        if user is None:
            burn_password_check(password)
            return None
        if not verify_password(password, user.password_hash) or not user.is_active:
            return None
        return user
