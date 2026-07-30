from datetime import datetime

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=255)
    acts_target: int = Field(..., gt=0, le=10000)
    month: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")


class GoalUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=255)
    acts_target: int | None = Field(None, gt=0, le=10000)


class GoalResponse(BaseModel):
    id: int
    title: str
    subtitle: str | None
    acts_target: int
    acts_done: int
    status: str
    completed_at: datetime | None
    month: str | None
    created_at: datetime
    progress: float = 0.0

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]
    total: int
    active_count: int
    completed_count: int


class GoalProgressUpdate(BaseModel):
    acts_done: int = Field(..., ge=0)


class GoalStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(active|completed|archived|replaced)$")


class MonthlyReviewResponse(BaseModel):
    id: int
    year_month: str
    goals_completed: int
    goals_active: int
    total_acts_done: int
    streak_at_review: int
    action_taken: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MonthlyReviewCreate(BaseModel):
    action_taken: str | None = Field(None, pattern=r"^(continued|modified|replaced|skipped)$")
    notes: str | None = Field(None, max_length=1000)
    goals_completed: int = Field(0, ge=0)
    goals_active: int = Field(0, ge=0)
    total_acts_done: int = Field(0, ge=0)
    streak_at_review: int = Field(0, ge=0)


class MonthlyReviewCheck(BaseModel):
    """Response indicating whether a monthly review is due."""
    due: bool
    year_month: str
    last_review: MonthlyReviewResponse | None = None