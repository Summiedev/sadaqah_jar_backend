"""Notifications domain models."""

from datetime import datetime, timezone
from enum import Enum as PyEnum

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


class NotificationCategory(str, PyEnum):
    FAMILY = "family"
    JOURNEY = "journey"
    PRAYER = "prayer"
    ADHKAR = "adhkar"
    READING = "reading"
    REFLECTION = "reflection"
    CHARITY = "charity"
    ISLAMIC_OCCASIONS = "islamic_occasions"
    ANNOUNCEMENTS = "announcements"
    SECURITY = "security"
    SYSTEM = "system"


class SchedulingStrategy(str, PyEnum):
    IMMEDIATE = "immediate"
    EVENT_BASED = "event_based"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    RANDOMIZED = "randomized"
    CONTEXT_AWARE = "context_aware"
    PRAYER_RELATIVE = "prayer_relative"
    TIME_OF_DAY = "time_of_day"


class NotificationStatus(str, PyEnum):
    CREATED = "created"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False, index=True
    )

    # Delivery tracking (production-readiness)
    status: Mapped[str] = mapped_column(
        String(16), default=NotificationStatus.CREATED.value, nullable=False, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_user_status", "user_id", "status"),
    )


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    strategy_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


class ScheduledNotification(Base):
    """A durable, idempotent record of a reminder queued for delivery."""

    __tablename__ = "scheduled_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("notification_templates.id", ondelete="CASCADE"), nullable=False
    )
    local_date: Mapped[str] = mapped_column(String(10), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="scheduled", nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "template_id",
            "local_date",
            name="uq_scheduled_notification_daily",
        ),
        Index("ix_scheduled_notifications_due", "status", "scheduled_for"),
    )
