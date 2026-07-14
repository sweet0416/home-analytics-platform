from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    code: str = "OK"
    message: str = "success"
    data: T | None = None
    trace_id: str | None = None


class Pagination(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination


def ok(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(data=data, message=message)

