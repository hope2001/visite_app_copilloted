from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import Role
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(enum_column_type(Role, name="role"))
    is_active: Mapped[bool] = mapped_column(default=True)
