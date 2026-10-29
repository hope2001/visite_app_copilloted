import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, VisitPassServiceDep, VisitServiceDep, require_roles
from app.api.v1.openapi import ERROR_RESPONSES
from app.domain.enums import Role
from app.models import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page, PageParams, build_page
from app.schemas.visit import (
    VisitCreate,
    VisitFilters,
    VisitorPassLookup,
    VisitorPassRead,
    VisitRead,
)

router = APIRouter(prefix="/visits", tags=["visits"], responses=ERROR_RESPONSES)

RegistrarUser = Annotated[User, Depends(require_roles(Role.EMPLOYEE, Role.ADMIN))]
FrontDeskUser = Annotated[User, Depends(require_roles(Role.SECURITY, Role.ADMIN))]


@router.post("", status_code=status.HTTP_201_CREATED)
def register_visit(data: VisitCreate, actor: RegistrarUser, visits: VisitServiceDep) -> VisitRead:
    return VisitRead.model_validate(visits.register_visit(actor, data))


@router.get("")
def list_visits(
    actor: RegistrarUser,
    visits: VisitServiceDep,
    filters: Annotated[VisitFilters, Query()],
    page: Annotated[PageParams, Query()],
) -> Page[VisitRead]:
    rows, total = visits.list_visits(actor, filters, page)
    return build_page(rows, total, page, VisitRead)


# Declared before "/{visit_id}" so "today" is never parsed as an id.
@router.get("/today")
def list_today_visits(
    _: FrontDeskUser,
    visits: VisitServiceDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[VisitRead]:
    return [VisitRead.model_validate(visit) for visit in visits.list_today(q)]


# POST so the pass code travels in the body and never ends up in URLs or access logs.
@router.post("/pass-lookup")
def lookup_visit_by_pass(
    data: VisitorPassLookup, actor: FrontDeskUser, passes: VisitPassServiceDep
) -> VisitRead:
    """Identifies the visit behind a scanned pass. Check-in stays a separate, explicit step."""
    return VisitRead.model_validate(passes.resolve(actor, data.code))


@router.get("/{visit_id}")
def get_visit(visit_id: uuid.UUID, actor: CurrentUser, visits: VisitServiceDep) -> VisitRead:
    return VisitRead.model_validate(visits.get_visit(actor, visit_id))


@router.post("/{visit_id}/check-in")
def check_in(visit_id: uuid.UUID, actor: FrontDeskUser, visits: VisitServiceDep) -> VisitRead:
    return VisitRead.model_validate(visits.check_in(actor, visit_id))


@router.post("/{visit_id}/check-out")
def check_out(visit_id: uuid.UUID, actor: FrontDeskUser, visits: VisitServiceDep) -> VisitRead:
    return VisitRead.model_validate(visits.check_out(actor, visit_id))


@router.post("/{visit_id}/cancel")
def cancel(visit_id: uuid.UUID, actor: RegistrarUser, visits: VisitServiceDep) -> VisitRead:
    return VisitRead.model_validate(visits.cancel(actor, visit_id))


@router.get("/{visit_id}/pass")
def get_visitor_pass(
    visit_id: uuid.UUID, actor: RegistrarUser, passes: VisitPassServiceDep
) -> VisitorPassRead:
    """QR pass for the registrant or host (or an admin) to send to the visitor."""
    return VisitorPassRead.model_validate(passes.issue(actor, visit_id))


@router.get("/{visit_id}/audit")
def get_visit_audit_trail(
    visit_id: uuid.UUID, actor: FrontDeskUser, visits: VisitServiceDep
) -> list[AuditLogRead]:
    entries = visits.list_audit_trail(actor, visit_id)
    return [AuditLogRead.model_validate(entry) for entry in entries]
