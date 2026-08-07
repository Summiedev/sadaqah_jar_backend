"""Family domain Pydantic schemas.

Follows the response envelope convention from app.core.envelope.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.envelope import Envelope


class FamilyRole(str, PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class InvitationStatus(str, PyEnum):
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


# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------


class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    cover_icon: str | None = None


class FamilyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    cover_icon: str | None = None


class FamilyMemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    role: FamilyRole
    joined_at: datetime
    contributed_today: bool = False

    model_config = {"from_attributes": True}


class FamilyGoalResponse(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    progress: float = 0.0
    acts_done: int = 0
    acts_target: int
    is_archived: bool = False
    completed_at: datetime | None = None
    created_by: int
    created_at: datetime
    milestones: list["FamilyGoalMilestoneResponse"] = []

    model_config = {"from_attributes": True}


class FamilyGoalMilestoneResponse(BaseModel):
    id: int
    goal_id: int
    title: str
    description: str | None = None
    target_value: int
    current_value: int = 0
    is_achieved: bool = False
    achieved_at: datetime | None = None
    sort_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class FamilyGoalMilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    target_value: int = Field(..., gt=0)
    sort_order: int = Field(0, ge=0)


class FamilyGoalMilestoneUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    target_value: int | None = Field(None, gt=0)
    current_value: int | None = Field(None, ge=0)
    sort_order: int | None = Field(None, ge=0)


class FamilyResponse(BaseModel):
    id: int
    name: str
    cover_icon: str | None = None
    invite_code: str
    member_count: int = 0
    goal_count: int = 0
    goal_label: str | None = None
    acts_done: int = 0
    acts_target: int = 0
    progress: float = 0.0
    days_remaining: int | None = None
    last_activity: str | None = None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FamilyDetailResponse(BaseModel):
    id: int
    name: str
    cover_icon: str | None = None
    invite_code: str
    members: list[FamilyMemberResponse] = []
    goals: list[FamilyGoalResponse] = []
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


class MemberRoleUpdate(BaseModel):
    role: FamilyRole


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


class InvitationCreate(BaseModel):
    """Create an invitation for a family."""


class InvitationResponse(BaseModel):
    id: int
    family_id: int
    family_name: str = ""
    invited_by: int
    invited_by_username: str = ""
    invite_code: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class JoinRequest(BaseModel):
    invite_code: str = Field(..., min_length=1, max_length=64)


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=255)
    acts_target: int = Field(..., gt=0)


class GoalUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=255)
    acts_target: int | None = Field(None, gt=0)
    acts_done: int | None = Field(None, ge=0)


# ---------------------------------------------------------------------------
# Prayer Requests
# ---------------------------------------------------------------------------


class PrayerRequestCreate(BaseModel):
    text: str = Field(..., min_length=1)
    is_private: bool = False


class PrayerRequestResponse(BaseModel):
    id: int
    family_id: int
    author_id: int
    author_name: str = ""
    text: str
    is_answered: bool
    is_private: bool
    response_counts: dict[str, int] = {}
    comment_counts: dict[str, int] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class PrayerRespond(BaseModel):
    response_type: PrayerResponseType


class PrayerCommentCreate(BaseModel):
    text: str = Field(..., min_length=1)


class PrayerCommentResponse(BaseModel):
    id: int
    prayer_request_id: int
    author_id: int
    author_name: str = ""
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


class ReflectionCreate(BaseModel):
    text: str = Field(..., min_length=1)


class ReflectionResponse(BaseModel):
    id: int
    family_id: int
    author_id: int
    author_name: str = ""
    text: str
    encouragement_counts: dict[str, int] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class ReflectionEncourage(BaseModel):
    encouragement_type: EncouragementType


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


class ActivityResponse(BaseModel):
    id: int
    actor_id: int | None = None
    actor_name: str | None = None
    event_type: EventType
    extra: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityPage(Envelope):
    pass


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    notification_preferences: dict[str, bool] | None = None


class SettingsResponse(BaseModel):
    id: int
    family_id: int
    notification_preferences: dict[str, bool] = {}
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
