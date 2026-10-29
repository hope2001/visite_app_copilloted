import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator, model_validator

from app.core.visitor_pass import MAX_PASS_CODE_LENGTH
from app.domain.enums import VisitStatus
from app.schemas.common import ApiModel, InputModel, QueryModel
from app.schemas.user import UserSummary

PHONE_PATTERN = r"^\+?[0-9][0-9 ()\-]{5,30}$"

NonBlank120 = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class VisitorInput(InputModel):
    full_name: NonBlank120
    email: EmailStr
    phone: Annotated[str, StringConstraints(pattern=PHONE_PATTERN)] | None = None
    company: NonBlank120

    @field_validator("phone", mode="before")
    @classmethod
    def _blank_phone_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.lower()


class VisitCreate(InputModel):
    visitor: VisitorInput
    purpose: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    expected_date: date
    host_id: uuid.UUID | None = None


class VisitFilters(QueryModel):
    status: VisitStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    host_id: uuid.UUID | None = None
    q: Annotated[str, StringConstraints(max_length=100)] | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> "VisitFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self


class VisitorRead(ApiModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    company: str


class VisitRead(ApiModel):
    id: uuid.UUID
    # Read from the per-visit snapshot, not the shared (mutable) visitor record.
    visitor: VisitorRead = Field(validation_alias="visitor_details")
    host: UserSummary
    registered_by: UserSummary
    purpose: str
    expected_date: date
    status: VisitStatus
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime


class VisitorPassRead(ApiModel):
    visit_id: uuid.UUID
    # Content of the QR code. Contains no personal data.
    code: str


class VisitorPassLookup(InputModel):
    code: Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASS_CODE_LENGTH)]
