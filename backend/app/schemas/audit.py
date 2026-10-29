import uuid
from datetime import date, datetime

from pydantic import model_validator

from app.domain.enums import AuditAction, VisitStatus
from app.schemas.common import ApiModel, QueryModel
from app.schemas.user import UserSummary


class AuditLogRead(ApiModel):
    id: uuid.UUID
    visit_id: uuid.UUID
    action: AuditAction
    from_status: VisitStatus | None
    to_status: VisitStatus
    performed_by: UserSummary
    occurred_at: datetime
    note: str | None


class AuditLogFilters(QueryModel):
    visit_id: uuid.UUID | None = None
    action: AuditAction | None = None
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> "AuditLogFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self
