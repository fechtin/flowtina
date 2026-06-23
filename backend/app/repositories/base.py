"""Generic repository implementing soft-delete-aware CRUD.

Repositories are the only layer allowed to talk to the database. They never make
external API calls and contain no business logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD operations shared by all repositories."""

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- internal helpers ---
    def _has_soft_delete(self) -> bool:
        return hasattr(self.model, "deleted_at")

    def _base_query(self, include_deleted: bool = False):
        stmt = select(self.model)
        if self._has_soft_delete() and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    # --- reads ---
    def get(self, obj_id: str, include_deleted: bool = False) -> ModelT | None:
        stmt = self._base_query(include_deleted).where(self.model.id == obj_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by(self, **filters: Any) -> ModelT | None:
        stmt = self._base_query()
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        order_by: str | None = "created_at",
        desc: bool = True,
        limit: int | None = None,
        offset: int | None = None,
        **filters: Any,
    ) -> list[ModelT]:
        stmt = self._base_query()
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            stmt = stmt.order_by(column.desc() if desc else column.asc())
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model)
        if self._has_soft_delete():
            stmt = stmt.where(self.model.deleted_at.is_(None))
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        return int(self.db.execute(stmt).scalar() or 0)

    # --- writes ---
    def create(self, **data: Any) -> ModelT:
        obj = self.model(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, obj: ModelT, **data: Any) -> ModelT:
        for key, value in data.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def soft_delete(self, obj: ModelT) -> None:
        if self._has_soft_delete():
            obj.deleted_at = datetime.now(timezone.utc)
            self.db.flush()
        else:
            self.db.delete(obj)
            self.db.flush()

    def hard_delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()
