from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.sql import ColumnElement


def build_search_filter(
    search: Optional[str],
    *fields,
) -> Optional[ColumnElement]:
    """Build case-insensitive LIKE clauses across string columns."""
    if not search or not fields:
        return None
    term = f"%{search.strip().lower()}%"
    clauses = []
    for field in fields:
        clauses.append(field.ilike(term) if hasattr(field, "ilike") else field.like(term))
    return or_(*clauses) if clauses else None


def apply_extra_filters(stmt, extra_filters: Optional[list[ColumnElement]]):
    if not extra_filters:
        return stmt
    for condition in extra_filters:
        stmt = stmt.where(condition)
    return stmt


def parse_sort(sort: Optional[str], allowed: dict[str, Any], default: Any):
    if not sort:
        return default
    descending = sort.startswith("-")
    key = sort[1:] if descending else sort
    column = allowed.get(key)
    if column is None:
        return default
    return column.desc() if descending else column.asc()
