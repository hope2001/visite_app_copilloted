import logging
import uuid
from dataclasses import dataclass

from app.core.visitor_pass import VisitorPassCodec
from app.domain.errors import ErrorCode, NotFoundError
from app.models import User, Visit
from app.services.visit_service import VisitService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VisitorPass:
    visit_id: uuid.UUID
    code: str


class VisitPassService:
    """Issues QR visitor passes and resolves scanned passes back to their visit.

    Resolving a pass only identifies the visit; admitting the visitor still goes through
    the normal check-in endpoint and its status, date and audit rules.
    """

    def __init__(self, visits: VisitService, codec: VisitorPassCodec) -> None:
        self._visits = visits
        self._codec = codec

    def issue(self, actor: User, visit_id: uuid.UUID) -> VisitorPass:
        visit = self._visits.get_visit(actor, visit_id)
        return VisitorPass(visit_id=visit.id, code=self._codec.encode(visit.id))

    def resolve(self, actor: User, code: str) -> Visit:
        visit_id = self._codec.decode(code)
        try:
            if visit_id is None:
                raise NotFoundError("Visit not found.")
            visit = self._visits.get_visit(actor, visit_id)
        except NotFoundError as exc:
            # One answer for malformed, forged and unknown passes: no oracle for guessing.
            raise NotFoundError(
                "This visitor pass is not valid. Find the visitor in today's list instead.",
                code=ErrorCode.VISITOR_PASS_INVALID,
            ) from exc
        logger.info(
            "Visitor pass resolved", extra={"visit_id": str(visit.id), "user_id": str(actor.id)}
        )
        return visit
