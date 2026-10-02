from __future__ import annotations

from math import ceil
from typing import Any, Optional, TypeVar

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


def normalize_pagination(page: int = 1, page_size: int = 20, *, max_page_size: int = 100) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), max_page_size)
    return page, page_size


def pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, int]:
    page, page_size = normalize_pagination(page, page_size)
    return {"page": page, "page_size": page_size}


def paginate_stmt(
    db: Session,
    stmt: Select[Any],
    *,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> tuple[list[T], int]:
    page, page_size = normalize_pagination(page, page_size, max_page_size=max_page_size)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0

    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def total_pages(total: int, page_size: int) -> int:
    return ceil(total / page_size) if page_size else 0
