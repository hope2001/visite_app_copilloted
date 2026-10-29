import uuid
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import AuditAction, VisitStatus
from app.models import AuditLog
from app.schemas.audit import AuditLogFilters
from app.schemas.common import PageParams


class AuditService:
    """Writes and reads the append-only audit trail. Writes never commit on their own:
    they join the caller's transaction so state change and audit entry are atomic."""

    def __init__(self, db: Session, timezone: ZoneInfo) -> None:
        self._db = db
        self._timezone = timezone

    def record(
        self,
        *,
        visit_id: uuid.UUID,
        action: AuditAction,
        from_status: VisitStatus | None,
        to_status: VisitStatus,
        actor_id: uuid.UUID,
        occurred_at: datetime,
    ) -> AuditLog:
        entry = AuditLog(
            visit_id=visit_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            performed_by_id=actor_id,
            occurred_at=occurred_at,
        )
        self._db.add(entry)
        return entry

    def list_for_visit(self, visit_id: uuid.UUID) -> Sequence[AuditLog]:
        return self._db.scalars(
            select(AuditLog)
            .where(AuditLog.visit_id == visit_id)
            .order_by(AuditLog.occurred_at, AuditLog.id)
        ).all()

    def list_logs(
        self, filters: AuditLogFilters, page: PageParams
    ) -> tuple[Sequence[AuditLog], int]:
        statement = select(AuditLog)
        if filters.visit_id:
            statement = statement.where(AuditLog.visit_id == filters.visit_id)
        if filters.action:
            statement = statement.where(AuditLog.action == filters.action)
        if filters.date_from:
            statement = statement.where(AuditLog.occurred_at >= self._start_of(filters.date_from))
        if filters.date_to:
            next_day = filters.date_to + timedelta(days=1)
            statement = statement.where(AuditLog.occurred_at < self._start_of(next_day))

        total = self._db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        items = self._db.scalars(
            statement.order_by(AuditLog.occurred_at.desc(), AuditLog.id)
            .offset(page.offset)
            .limit(page.size)
        ).all()
        return items, total

    def _start_of(self, day: date) -> datetime:
        """Start of a local (site timezone) day, as an aware datetime."""
        return datetime.combine(day, time.min, tzinfo=self._timezone)
