"""Persisted in-app announcements and per-user delivery receipts."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Broadcast(Base):
    __tablename__ = "broadcasts"
    __table_args__ = (
        Index("ix_broadcasts_active_window", "is_active", "starts_at", "ends_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cta_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cta_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audience: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    display_mode: Mapped[str] = mapped_column(
        String(32), default="until_dismissed", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


class BroadcastReceipt(Base):
    __tablename__ = "broadcast_receipts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "broadcast_id",
            name="uq_broadcast_receipt_user_broadcast",
        ),
        Index("ix_broadcast_receipts_user_broadcast", "user_id", "broadcast_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    broadcast_id: Mapped[int] = mapped_column(
        ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
