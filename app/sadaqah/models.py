"""Sadaqah domain models.

Activities are the atomic unit of goodness in Mizan.
An ActivityCompletion records that a user performed a specific act.

Design principles
-----------------
- No legacy jar/star metaphors in the data model.
- Modes (Personal / Family / Both) are execution contexts, not separate products.
- Family sharing is a property of a completion, not a separate domain.
- Events are published from the service layer so other domains (notifications,
  family, journey, analytics) can react without tight coupling.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.mixins import SoftDeleteMixin, TimestampMixin
from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ActivityType(str, PyEnum):
    """Canonical activity types derived from the Flutter `AddActScreen`."""

    MONEY = "money"
    FOOD = "food"
    KINDNESS = "kindness"
    DHIKR = "dhikr"
    PRAYER = "prayer"
    REMOVE_HARM = "remove_harm"
    SMILE = "smile"
    TIME = "time"


class ActivityContext(str, PyEnum):
    """Execution context for an activity completion."""

    PERSONAL = "personal"
    FAMILY = "family"
    BOTH = "both"


class ActivityCompletion(Base, TimestampMixin, SoftDeleteMixin):
    """Records a single instance of a user completing an activity.

    This is the single source of truth for all act-of-worship tracking.
    Legacy `sadaqah_logs` and `jars` are replaced by this model.
    """

    __tablename__ = "activity_completions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, native_enum=False), nullable=False, index=True
    )

    context: Mapped[ActivityContext] = mapped_column(
        Enum(ActivityContext, native_enum=False),
        nullable=False,
        index=True,
    )

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    family_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("families.id", ondelete="SET NULL"), nullable=True, index=True
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, default=_utcnow
    )

    # Denormalized snapshot fields for fast analytics without JOINs
    stars_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    friday_boost: Mapped[bool] = mapped_column(Boolean, default=False)
    ramadan_bonus: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_activity_completions_user_date", "user_id", "completed_at"),
        Index("ix_activity_completions_user_type", "user_id", "activity_type"),
        Index("ix_activity_completions_family", "family_id", "completed_at"),
    )


class ActivitySession(Base, TimestampMixin, SoftDeleteMixin):
    """Tracks a time-bound activity session (e.g., prayer, reading, adhkar).

    Not every activity needs a session — discrete acts (smile, charity) do not.
    Continuous acts (prayer, reading, dhikr) may.
    """

    __tablename__ = "activity_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, native_enum=False), nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    context: Mapped[ActivityContext] = mapped_column(
        Enum(ActivityContext, native_enum=False), nullable=False, index=True
    )

    family_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("families.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_activity_sessions_user_started", "user_id", "started_at"),
    )


class ActivityStreak(Base, TimestampMixin):
    """Per-user, per-activity-type streak counter.

    Computed lazily from activity_completions to avoid real-time aggregation.
    """

    __tablename__ = "activity_streaks"

    __table_args__ = (
        UniqueConstraint("user_id", "activity_type", name="uq_activity_streak"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, native_enum=False), nullable=False, index=True
    )

    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
