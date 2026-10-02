from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Union[dict, list, str]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: Optional[str] = None
