"""Family domain models.

Every model follows the conventions established in app/users/models.py:
- soft delete via deleted_at (nullable)
- created_at / updated_at timestamps
- _utcnow helper for default timestamps
- native_enum=False for SQLAlchemy Enum
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FamilyRole(PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class InvitationStatus(PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PrayerResponseType(str, PyEnum):
    AMEEN = "ameen"
    GRANT_EASE = "grant_ease"
    ACCEPT = "accept"


class EncouragementType(str, PyEnum):
    MAY_ALLAH_ACCEPT = "may_allah_accept"
    AMEEN = "ameen"
    BARAKALLAHU_FEEK = "barakallahu_feek"
    MAY_ALLAH_INCREASE = "may_allah_increase"


class EventType(str, PyEnum):
    FAMILY_CREATED = "family.created"
    MEMBER_JOINED = "member.joined"
    MEMBER_LEFT = "member.left"
    MEMBER_ROLE_CHANGED = "member.role_changed"
    GOAL_CREATED = "goal.created"
    GOAL_COMPLETED = "goal.completed"
    PRAYER_REQUEST_CREATED = "prayer_request.created"
    PRAYER_REQUEST_ANSWERED = "prayer_request.answered"
    REFLECTION_SHARED = "reflection.shared"
    INVITATION_ACCEPTED = "invitation.accepted"
    INVITATION_DECLINED = "invitation.declined"
    ACT_ADDED = "act.added"


# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------


class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cover_icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    members = relationship(
        "FamilyMember", back_populates="family", cascade="all, delete-orphan"
    )
    invitations = relationship(
        "FamilyInvitation", back_populates="family", cascade="all, delete-orphan"
    )
    goals = relationship(
        "FamilyGoal", back_populates="family", cascade="all, delete-orphan"
    )
    prayer_requests = relationship(
        "PrayerRequest", back_populates="family", cascade="all, delete-orphan"
    )
    reflections = relationship(
        "FamilyReflection", back_populates="family", cascade="all, delete-orphan"
    )
    activities = relationship(
        "FamilyActivity", back_populates="family", cascade="all, delete-orphan"
    )
    settings = relationship(
        "FamilySettings",
        back_populates="family",
        uselist=False,
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# FamilyMember
# ---------------------------------------------------------------------------


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[FamilyRole] = mapped_column(
        Enum(FamilyRole, native_enum=False), default=FamilyRole.MEMBER, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    family = relationship("Family", back_populates="members")

    __table_args__ = (
        UniqueConstraint("family_id", "user_id", name="uq_family_member"),
        Index("ix_family_members_user_active", "user_id", "deleted_at"),
    )


# ---------------------------------------------------------------------------
# FamilyInvitation
# ---------------------------------------------------------------------------


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invited_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    invite_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, native_enum=False),
        default=InvitationStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    family = relationship("Family", back_populates="invitations")

    __table_args__ = (
        Index("ix_family_invitations_family_status", "family_id", "status"),
    )


# ---------------------------------------------------------------------------
# FamilyGoal
# ---------------------------------------------------------------------------


class FamilyGoal(Base):
    __tablename__ = "family_goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acts_target: Mapped[int] = mapped_column(Integer, nullable=False)
    acts_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    family = relationship("Family", back_populates="goals")
    milestones = relationship(
        "FamilyGoalMilestone", back_populates="goal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_family_goals_active", "family_id", "is_archived", "deleted_at"),
    )


# ---------------------------------------------------------------------------
# PrayerRequest
# ---------------------------------------------------------------------------


class PrayerRequest(Base):
    __tablename__ = "prayer_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_answered: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    family = relationship("Family", back_populates="prayer_requests")
    responses = relationship(
        "PrayerRequestResponse",
        back_populates="prayer_request",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "PrayerComment", back_populates="prayer_request", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_prayer_requests_list", "family_id", "is_answered", "created_at"),
    )


class PrayerComment(Base):
    __tablename__ = "prayer_comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prayer_request_id: Mapped[int] = mapped_column(
        ForeignKey("prayer_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    prayer_request = relationship("PrayerRequest", back_populates="comments")


# ---------------------------------------------------------------------------
# PrayerRequestResponse
# ---------------------------------------------------------------------------


class PrayerRequestResponse(Base):
    __tablename__ = "prayer_request_responses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prayer_request_id: Mapped[int] = mapped_column(
        ForeignKey("prayer_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_type: Mapped[PrayerResponseType] = mapped_column(
        Enum(PrayerResponseType, native_enum=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    prayer_request = relationship("PrayerRequest", back_populates="responses")

    __table_args__ = (
        UniqueConstraint(
            "prayer_request_id",
            "user_id",
            "response_type",
            name="uq_prayer_response",
        ),
    )


# ---------------------------------------------------------------------------
# FamilyReflection
# ---------------------------------------------------------------------------


class FamilyReflection(Base):
    __tablename__ = "family_reflections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    family = relationship("Family", back_populates="reflections")
    encouragements = relationship(
        "ReflectionEncouragement",
        back_populates="reflection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_family_reflections_list", "family_id", "created_at"),)


# ---------------------------------------------------------------------------
# ReflectionEncouragement
# ---------------------------------------------------------------------------


class ReflectionEncouragement(Base):
    __tablename__ = "reflection_encouragements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reflection_id: Mapped[int] = mapped_column(
        ForeignKey("family_reflections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    encouragement_type: Mapped[EncouragementType] = mapped_column(
        Enum(EncouragementType, native_enum=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    reflection = relationship("FamilyReflection", back_populates="encouragements")

    __table_args__ = (
        UniqueConstraint(
            "reflection_id",
            "user_id",
            "encouragement_type",
            name="uq_reflection_encouragement",
        ),
    )


# ---------------------------------------------------------------------------
# FamilyActivity
# ---------------------------------------------------------------------------


class FamilyActivity(Base):
    __tablename__ = "family_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False), nullable=False, index=True
    )
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    family = relationship("Family", back_populates="activities")

    __table_args__ = (
        Index("ix_family_activities_timeline", "family_id", "created_at", "id"),
        UniqueConstraint("request_id", name="uq_family_activity_request_id"),
    )


# ---------------------------------------------------------------------------
# FamilySettings
# ---------------------------------------------------------------------------


class FamilySettings(Base):
    __tablename__ = "family_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    notification_preferences: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    family = relationship("Family", back_populates="settings")


# ---------------------------------------------------------------------------
# FamilyGoalMilestone
# ---------------------------------------------------------------------------


class FamilyGoalMilestone(Base):
    __tablename__ = "family_goal_milestones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("family_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_achieved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    goal = relationship("FamilyGoal", back_populates="milestones")

    __table_args__ = (Index("ix_family_goal_milestones_goal", "goal_id", "sort_order"),)
