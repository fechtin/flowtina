"""Common response envelopes and shared schema helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base schema that reads attributes from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class APIResponse(BaseModel, Generic[T]):
    """Standard success envelope: ``{success, message, data}``."""

    success: bool = True
    message: str = ""
    data: T | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta


class TimestampedSchema(ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


def ok(data: Any = None, message: str = "") -> dict[str, Any]:
    """Build a success envelope dict (used by routers)."""
    return {"success": True, "message": message, "data": data}
