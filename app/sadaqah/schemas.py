"""Sadaqah domain Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.sadaqah.models import ActivityContext, ActivityType


# ---------------------------------------------------------------------------
# Activity Completions
# ---------------------------------------------------------------------------


class ActivityCompletionCreate(BaseModel):
    activity_type: ActivityType
    context: ActivityContext = ActivityContext.PERSONAL
    note: Optional[str] = Field(None, max_length=500)
    family_id: Optional[int] = None
    completed_at: Optional[datetime] = None


class ActivityCompletionResponse(BaseModel):
    id: int
    user_id: int
    activity_type: ActivityType
    context: ActivityContext
    note: Optional[str]
    family_id: Optional[int]
    completed_at: datetime
    created_at: datetime
    stars_earned: int
    friday_boost: bool
    ramadan_bonus: bool

    model_config = {"from_attributes": True}


class ActivityCompletionsPage(BaseModel):
    data: list[ActivityCompletionResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Activity Sessions
# ---------------------------------------------------------------------------


class ActivitySessionCreate(BaseModel):
    activity_type: ActivityType
    context: ActivityContext = ActivityContext.PERSONAL
    note: Optional[str] = Field(None, max_length=500)
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    family_id: Optional[int] = None


class ActivitySessionResponse(BaseModel):
    id: int
    user_id: int
    activity_type: ActivityType
    context: ActivityContext
    note: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    family_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivitySessionsPage(BaseModel):
    data: list[ActivitySessionResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Activity Streaks
# ---------------------------------------------------------------------------


class ActivityStreakResponse(BaseModel):
    id: int
    activity_type: ActivityType
    current_streak: int
    longest_streak: int
    last_completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class ActivitySummaryResponse(BaseModel):
    total_completions: int
    total_stars_earned: int
    current_streak: int
    longest_streak: int
    most_common_activity: Optional[str]
    friday_boost_count: int
    ramadan_bonus_count: int


class ActivityHeatmapResponse(BaseModel):
    data: dict[str, int]


class CategoryBreakdownResponse(BaseModel):
    category: str
    count: int
    stars: int
