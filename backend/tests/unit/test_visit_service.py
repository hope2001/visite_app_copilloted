"""Service-level tests for behaviour that is hard to trigger through HTTP."""

import pytest
from fastapi import FastAPI
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import VisitStatus
from app.domain.errors import InvalidStateTransitionError
from app.models import AuditLog, User, Visit
from app.schemas.visit import VisitCreate, VisitorInput
from app.services.visit_service import VisitService
from tests.conftest import TODAY, FixedClock


def test_concurrent_status_change_is_detected_and_rolled_back(
    app: FastAPI, db: Session, users: dict[str, User], clock: FixedClock, settings: Settings
) -> None:
    service = VisitService(db, clock, settings.timezone)
    visit = service.register_visit(
        users["employee"],
        VisitCreate(
            visitor=VisitorInput(full_name="Jane", email="jane@contoso.com", company="Contoso"),
            purpose="Meeting",
            expected_date=TODAY,
        ),
    )
    # Another operator checks the visitor in from a separate session.
    with app.state.session_factory() as other:
        other.execute(
            update(Visit).where(Visit.id == visit.id).values(status=VisitStatus.CHECKED_IN)
        )
        other.commit()

    # Our session still holds the stale EXPECTED state in its identity map.
    with pytest.raises(InvalidStateTransitionError):
        service.check_in(users["security"], visit.id)

    audit_count = db.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.visit_id == visit.id)
    )
    assert audit_count == 1
