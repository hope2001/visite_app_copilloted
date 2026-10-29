from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import Settings
from app.core.security import decode_access_token
from app.core.visitor_pass import VisitorPassCodec
from app.domain.enums import Role
from app.domain.errors import AuthenticationError, ErrorCode, PermissionDeniedError
from app.models import User
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.visit_pass_service import VisitPassService
from app.services.visit_service import VisitService

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_db(request: Request) -> Iterator[Session]:
    """One session per request. Services commit explicitly; anything uncommitted is rolled back."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(get_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    db: DbSession,
    settings: SettingsDep,
) -> User:
    if not token:
        raise AuthenticationError("Authentication required.", code=ErrorCode.AUTH_TOKEN_INVALID)
    claims = decode_access_token(token, settings)
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(
            "Invalid authentication token.", code=ErrorCode.AUTH_TOKEN_INVALID
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Route-level RBAC. Object-level checks live in `app.domain.policies`."""
    allowed = frozenset(roles)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError("You do not have permission to perform this action.")
        return user

    return dependency


def get_auth_service(request: Request, db: DbSession, settings: SettingsDep) -> AuthService:
    state = request.app.state
    return AuthService(db, settings, state.login_limiter, state.account_login_limiter)


def get_visit_service(db: DbSession, clock: ClockDep, settings: SettingsDep) -> VisitService:
    return VisitService(db, clock, settings.timezone)


def get_visit_pass_service(
    visits: Annotated[VisitService, Depends(get_visit_service)], settings: SettingsDep
) -> VisitPassService:
    return VisitPassService(visits, VisitorPassCodec(settings.jwt_secret_key))


def get_audit_service(db: DbSession, settings: SettingsDep) -> AuditService:
    return AuditService(db, settings.timezone)


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
VisitServiceDep = Annotated[VisitService, Depends(get_visit_service)]
VisitPassServiceDep = Annotated[VisitPassService, Depends(get_visit_pass_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
