"""Reusable SQLAlchemy model mixins."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(default=1, nullable=False)


class OwnershipMixin:
    created_by: Mapped[Optional[int]] = mapped_column(index=True, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(index=True, nullable=True)
