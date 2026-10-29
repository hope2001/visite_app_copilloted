from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import HOST_ROLES
from app.models import User


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_hosts(self) -> Sequence[User]:
        return self._db.scalars(
            select(User)
            .where(User.is_active.is_(True), User.role.in_(HOST_ROLES))
            .order_by(User.full_name, User.id)
        ).all()
