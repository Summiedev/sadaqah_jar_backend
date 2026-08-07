"""Shared validators for Mizan domains."""

import re
from datetime import datetime


def is_valid_uuid(value: str) -> bool:
    pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )
    return bool(pattern.match(value))


def is_valid_invite_code(value: str) -> bool:
    return bool(re.match(r"^[A-Z0-9]{6,12}$", value))


def is_valid_slug(value: str) -> bool:
    return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value))


def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value))


def is_valid_name(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z\s'-]{2,100}$", value))


def validate_pagination(
    limit: int | None, offset: int | None, max_limit: int = 100
) -> dict[str, int]:
    limit = min(limit or 20, max_limit)
    offset = max(offset or 0, 0)
    return {"limit": limit, "offset": offset}


def validate_date_range(
    start: datetime | None, end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must be before end_date")
    return start, end
