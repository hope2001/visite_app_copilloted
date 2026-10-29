from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.domain.errors import ErrorCode

MAX_PAGE_SIZE = 100


class ApiModel(BaseModel):
    """Base for response models built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class InputModel(BaseModel):
    """Base for request bodies: unknown fields are rejected (prevents mass assignment)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QueryModel(BaseModel):
    """Base for query-string models (several may share one query string)."""

    model_config = ConfigDict(str_strip_whitespace=True)


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PageParams(QueryModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int


def build_page[ModelT: BaseModel](
    rows: Iterable[object], total: int, params: PageParams, model: type[ModelT]
) -> Page[ModelT]:
    return Page[ModelT](
        items=[model.model_validate(row) for row in rows],
        total=total,
        page=params.page,
        size=params.size,
    )
