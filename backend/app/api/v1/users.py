from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import UserServiceDep, require_roles
from app.api.v1.openapi import ERROR_RESPONSES
from app.domain.enums import Role
from app.models import User
from app.schemas.user import UserSummary

router = APIRouter(prefix="/users", tags=["users"], responses=ERROR_RESPONSES)


@router.get("/hosts")
def list_hosts(
    _: Annotated[User, Depends(require_roles(Role.EMPLOYEE, Role.ADMIN))],
    users: UserServiceDep,
) -> list[UserSummary]:
    return [UserSummary.model_validate(user) for user in users.list_hosts()]
