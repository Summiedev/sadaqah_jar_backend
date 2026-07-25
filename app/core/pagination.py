"""Cursor-based pagination utilities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from sqlalchemy import Column, asc
from sqlalchemy.orm import Query

T = TypeVar("T")


@dataclass
class CursorPageResult(Generic[T]):
    data: list[T]
    next_cursor: str | None = None
    has_more: bool = False


def apply_cursor_pagination(
    query: Query,
    cursor: str | None = None,
    limit: int = 20,
    cursor_field: Column | None = None,
) -> CursorPageResult:
    if cursor_field is None:
        cursor_field = query.column_descriptions[0]["entity"].id

    if cursor:
        try:
            cursor_value = datetime.fromisoformat(cursor)
            query = query.filter(cursor_field > cursor_value)
        except (ValueError, TypeError):
            pass

    rows = query.order_by(asc(cursor_field)).limit(limit + 1).all()

    has_more = len(rows) > limit
    data = rows[:limit]

    next_cursor = None
    if has_more and data:
        last = data[-1]
        cursor_value = getattr(last, cursor_field.key)
        if isinstance(cursor_value, datetime):
            next_cursor = cursor_value.isoformat()

    return CursorPageResult(data=data, next_cursor=next_cursor, has_more=has_more)
