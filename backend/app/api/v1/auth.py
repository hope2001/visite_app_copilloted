from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: AuthServiceDep,
) -> TokenResponse:
    client_address = request.client.host if request.client else "unknown"
    token = auth.login(form.username, form.password, client_address)
    return TokenResponse(access_token=token.value, expires_in=token.expires_in_seconds)


@router.get("/me", responses={401: {"model": ErrorResponse}})
def read_current_user(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
