"""Personal user goals model.

Tracks individual goals and milestones for personal mode users.
Family goals are handled by the family module (FamilyGoal model).
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
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


class GoalStatus(PyEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    REPLACED = "replaced"


class UserGoal(Base):
    """A personal goal set by a user during onboarding or later."""

    __tablename__ = "user_goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acts_target: Mapped[int] = mapped_column(Integer, nullable=False)
    acts_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, native_enum=False),
        default=GoalStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    month: Mapped[str | None] = mapped_column(
        String(7), nullable=True
    )  # YYYY-MM format for monthly goals
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_user_goals_active", "user_id", "status", "deleted_at"),
        Index("ix_user_goals_month", "user_id", "month", "status"),
    )


class MonthlyGoalReview(Base):
    """Tracks monthly goal review check-ins for users."""

    __tablename__ = "monthly_goal_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM format
    goals_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goals_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_acts_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_at_review: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    action_taken: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # continued, modified, replaced, skipped
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "year_month", name="uq_user_monthly_review"),
    )
