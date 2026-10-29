import uuid

from app.domain.enums import Role
from app.schemas.common import ApiModel


class UserSummary(ApiModel):
    id: uuid.UUID
    full_name: str
    email: str


class UserRead(UserSummary):
    role: Role
