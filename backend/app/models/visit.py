import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import VisitStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.user import User
from app.models.visitor import Visitor


@dataclass(frozen=True, slots=True)
class VisitorDetails:
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    company: str


class Visit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visits"
    __table_args__ = (Index("ix_visits_expected_date_status", "expected_date", "status"),)

    visitor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visitors.id"), index=True)
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    registered_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    # Visitor details as registered for this visit. The shared `Visitor` row is refreshed by
    # later registrations; the snapshot stops one employee from changing the identity the
    # front desk verifies for another employee's visit.
    visitor_full_name: Mapped[str] = mapped_column(String(120))
    visitor_phone: Mapped[str | None] = mapped_column(String(32))
    visitor_company: Mapped[str] = mapped_column(String(120))

    purpose: Mapped[str] = mapped_column(String(500))
    expected_date: Mapped[date]
    status: Mapped[VisitStatus] = mapped_column(
        enum_column_type(VisitStatus, name="status"), default=VisitStatus.EXPECTED
    )

    checked_in_at: Mapped[datetime | None]
    checked_in_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    checked_out_at: Mapped[datetime | None]
    checked_out_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None]

    visitor: Mapped[Visitor] = relationship(lazy="joined")
    host: Mapped[User] = relationship(foreign_keys=[host_id], lazy="joined")
    registered_by: Mapped[User] = relationship(foreign_keys=[registered_by_id], lazy="joined")

    @property
    def visitor_details(self) -> VisitorDetails:
        return VisitorDetails(
            id=self.visitor_id,
            full_name=self.visitor_full_name,
            email=self.visitor.email,
            phone=self.visitor_phone,
            company=self.visitor_company,
        )
