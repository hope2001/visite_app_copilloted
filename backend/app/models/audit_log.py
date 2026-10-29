import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import AuditAction, VisitStatus
from app.models.base import Base, UUIDPrimaryKeyMixin, enum_column_type
from app.models.user import User


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only record of visit lifecycle events. Never updated or deleted."""

    __tablename__ = "audit_logs"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), index=True)
    action: Mapped[AuditAction] = mapped_column(enum_column_type(AuditAction, name="action"))
    from_status: Mapped[VisitStatus | None] = mapped_column(
        enum_column_type(VisitStatus, name="from_status")
    )
    to_status: Mapped[VisitStatus] = mapped_column(enum_column_type(VisitStatus, name="to_status"))
    performed_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(index=True)
    note: Mapped[str | None] = mapped_column(String(500))

    performed_by: Mapped[User] = relationship(lazy="joined")
