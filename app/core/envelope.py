"""Standard API envelope and pagination models."""

from typing import Any

from pydantic import BaseModel


class Meta(BaseModel):
    total: int | None = None
    next_cursor: str | None = None
    has_more: bool = False


class Envelope(BaseModel):
    data: Any
    meta: Meta | None = None
    message: str | None = None


class CursorPage(BaseModel):
    data: list
    next_cursor: str | None = None
    has_more: bool = False
