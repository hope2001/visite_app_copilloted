from typing import Any

from app.schemas.common import ErrorResponse

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status_code: {"model": ErrorResponse} for status_code in (401, 403, 404, 409, 422, 500)
}
