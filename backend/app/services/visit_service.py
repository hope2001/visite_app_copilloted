import uuid
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy import CursorResult, Select, case, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.clock import Clock, local_today
from app.domain.enums import HOST_ROLES, AuditAction, VisitStatus
from app.domain.errors import (
    BusinessRuleError,
    ConflictError,
    ErrorCode,
    FieldIssue,
    InvalidStateTransitionError,
    NotFoundError,
    PermissionDeniedError,
)
from app.domain.policies import can_cancel_visit, can_view_visit, scope_visit_query
from app.domain.visit_status import ensure_transition
from app.models import AuditLog, User, Visit, Visitor
from app.schemas.common import PageParams
from app.schemas.visit import VisitCreate, VisitFilters, VisitorInput
from app.services.audit_service import AuditService

_TODAY_STATUS_ORDER = case(
    {
        VisitStatus.EXPECTED: 0,
        VisitStatus.CHECKED_IN: 1,
        VisitStatus.CHECKED_OUT: 2,
        VisitStatus.CANCELLED: 3,
    },
    value=Visit.status,
)


class VisitService:
    def __init__(self, db: Session, clock: Clock, timezone: ZoneInfo) -> None:
        self._db = db
        self._clock = clock
        self._timezone = timezone
        self._audit = AuditService(db, timezone)

    def today(self) -> date:
        return local_today(self._clock, self._timezone)

    # ---- Queries -------------------------------------------------------------------------

    def get_visit(self, actor: User, visit_id: uuid.UUID) -> Visit:
        visit = self._db.get(Visit, visit_id)
        if visit is None or not can_view_visit(actor, visit):
            # Same response whether it is missing or not visible: does not leak existence.
            raise NotFoundError("Visit not found.", code=ErrorCode.VISIT_NOT_FOUND)
        return visit

    def list_visits(
        self, actor: User, filters: VisitFilters, page: PageParams
    ) -> tuple[Sequence[Visit], int]:
        statement = self._apply_filters(scope_visit_query(actor, select(Visit)), filters)
        total = self._db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        items = self._db.scalars(
            statement.order_by(Visit.expected_date.desc(), Visit.created_at.desc(), Visit.id)
            .offset(page.offset)
            .limit(page.size)
        ).all()
        return items, total

    def list_today(self, search: str | None) -> Sequence[Visit]:
        statement = select(Visit).where(Visit.expected_date == self.today())
        statement = self._apply_search(statement, search)
        return self._db.scalars(
            statement.order_by(_TODAY_STATUS_ORDER, Visit.visitor_full_name, Visit.id)
        ).all()

    def list_audit_trail(self, actor: User, visit_id: uuid.UUID) -> Sequence[AuditLog]:
        visit = self.get_visit(actor, visit_id)
        return self._audit.list_for_visit(visit.id)

    # ---- Commands ------------------------------------------------------------------------

    def register_visit(self, actor: User, data: VisitCreate) -> Visit:
        self._ensure_not_in_past(data.expected_date)
        host = self._resolve_host(actor, data.host_id)
        visitor = self._upsert_visitor(data.visitor)

        visit = Visit(
            visitor=visitor,
            visitor_full_name=data.visitor.full_name,
            visitor_phone=data.visitor.phone,
            visitor_company=data.visitor.company,
            host=host,
            registered_by=actor,
            purpose=data.purpose,
            expected_date=data.expected_date,
            status=VisitStatus.EXPECTED,
        )
        self._db.add(visit)
        self._db.flush()
        self._audit.record(
            visit_id=visit.id,
            action=AuditAction.VISIT_CREATED,
            from_status=None,
            to_status=VisitStatus.EXPECTED,
            actor_id=actor.id,
            occurred_at=self._clock.now(),
        )
        self._db.commit()
        return visit

    def check_in(self, actor: User, visit_id: uuid.UUID) -> Visit:
        visit = self.get_visit(actor, visit_id)
        ensure_transition(visit.status, VisitStatus.CHECKED_IN)
        if visit.expected_date != self.today():
            raise ConflictError(
                "This visit is not scheduled for today.", code=ErrorCode.VISIT_NOT_DUE_TODAY
            )
        now = self._clock.now()
        return self._transition(
            visit,
            actor,
            target=VisitStatus.CHECKED_IN,
            action=AuditAction.CHECKED_IN,
            occurred_at=now,
            changes={"checked_in_at": now, "checked_in_by_id": actor.id},
        )

    def check_out(self, actor: User, visit_id: uuid.UUID) -> Visit:
        visit = self.get_visit(actor, visit_id)
        ensure_transition(visit.status, VisitStatus.CHECKED_OUT)
        now = self._clock.now()
        return self._transition(
            visit,
            actor,
            target=VisitStatus.CHECKED_OUT,
            action=AuditAction.CHECKED_OUT,
            occurred_at=now,
            changes={"checked_out_at": now, "checked_out_by_id": actor.id},
        )

    def cancel(self, actor: User, visit_id: uuid.UUID) -> Visit:
        visit = self.get_visit(actor, visit_id)
        if not can_cancel_visit(actor, visit):
            raise PermissionDeniedError(
                "Only the employee who registered this visit or an administrator can cancel it."
            )
        ensure_transition(visit.status, VisitStatus.CANCELLED)
        now = self._clock.now()
        return self._transition(
            visit,
            actor,
            target=VisitStatus.CANCELLED,
            action=AuditAction.CANCELLED,
            occurred_at=now,
            changes={"cancelled_at": now},
        )

    # ---- Helpers -------------------------------------------------------------------------

    def _transition(
        self,
        visit: Visit,
        actor: User,
        *,
        target: VisitStatus,
        action: AuditAction,
        occurred_at: datetime,
        changes: dict[str, Any],
    ) -> Visit:
        """Atomic compare-and-set on the status, plus the audit entry in the same transaction.

        The WHERE on the current status guarantees two concurrent operators cannot both win.
        """
        previous = visit.status
        result = self._db.execute(
            update(Visit)
            .where(Visit.id == visit.id, Visit.status == previous)
            .values(status=target, updated_at=occurred_at, **changes)
            .execution_options(synchronize_session=False)
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            self._db.rollback()
            raise InvalidStateTransitionError(
                "This visit was just updated by someone else. Refresh and try again."
            )

        self._audit.record(
            visit_id=visit.id,
            action=action,
            from_status=previous,
            to_status=target,
            actor_id=actor.id,
            occurred_at=occurred_at,
        )
        self._db.commit()
        self._db.refresh(visit)
        return visit

    def _ensure_not_in_past(self, expected_date: date) -> None:
        if expected_date < self.today():
            raise BusinessRuleError(
                "The expected visit date cannot be in the past.",
                details=(FieldIssue("expected_date", "Must be today or a future date."),),
            )

    def _resolve_host(self, actor: User, host_id: uuid.UUID | None) -> User:
        if host_id is None or host_id == actor.id:
            return actor
        host = self._db.get(User, host_id)
        if host is None or not host.is_active or host.role not in HOST_ROLES:
            raise BusinessRuleError(
                "The selected host does not exist or cannot receive visitors.",
                code=ErrorCode.HOST_NOT_FOUND,
                details=(FieldIssue("host_id", "Unknown or inactive host."),),
            )
        return host

    def _upsert_visitor(self, data: VisitorInput) -> Visitor:
        visitor = self._db.scalar(select(Visitor).where(Visitor.email == data.email))
        if visitor is None:
            visitor = Visitor(email=data.email)
            self._db.add(visitor)
        visitor.full_name = data.full_name
        visitor.phone = data.phone
        visitor.company = data.company
        return visitor

    def _apply_filters(
        self, statement: Select[tuple[Visit]], filters: VisitFilters
    ) -> Select[tuple[Visit]]:
        if filters.status:
            statement = statement.where(Visit.status == filters.status)
        if filters.date_from:
            statement = statement.where(Visit.expected_date >= filters.date_from)
        if filters.date_to:
            statement = statement.where(Visit.expected_date <= filters.date_to)
        if filters.host_id:
            statement = statement.where(Visit.host_id == filters.host_id)
        if filters.q:
            statement = self._apply_search(statement, filters.q)
        return statement

    @staticmethod
    def _apply_search(statement: Select[tuple[Visit]], search: str | None) -> Select[tuple[Visit]]:
        """Searches the per-visit visitor snapshot. Wildcards in user input are escaped."""
        if not search or not search.strip():
            return statement
        term = search.strip()
        return statement.where(
            or_(
                Visit.visitor_full_name.icontains(term, autoescape=True),
                Visit.visitor_company.icontains(term, autoescape=True),
            )
        )
