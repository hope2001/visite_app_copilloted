from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AuditServiceDep, require_roles
from app.api.v1.openapi import ERROR_RESPONSES
from app.domain.enums import Role
from app.models import User
from app.schemas.audit import AuditLogFilters, AuditLogRead
from app.schemas.common import Page, PageParams, build_page

router = APIRouter(prefix="/audit-logs", tags=["audit"], responses=ERROR_RESPONSES)


@router.get("")
def list_audit_logs(
    _: Annotated[User, Depends(require_roles(Role.ADMIN))],
    audit: AuditServiceDep,
    filters: Annotated[AuditLogFilters, Query()],
    page: Annotated[PageParams, Query()],
) -> Page[AuditLogRead]:
    rows, total = audit.list_logs(filters, page)
    return build_page(rows, total, page, AuditLogRead)
