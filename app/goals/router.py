"""API router for user goals and monthly reviews."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.goals import service
from app.goals.schemas import (
    GoalCreate,
    GoalProgressUpdate,
    GoalStatusUpdate,
    GoalUpdate,
    MonthlyReviewCreate,
)

router = APIRouter(prefix="/goals", tags=["goals"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# User Goals
# ---------------------------------------------------------------------------


@router.post("", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_goal(
    data: GoalCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Create a new personal goal."""
    result = service.create_goal(db, current_user.id, data)
    return Envelope(data=result)


@router.get("", response_model=Envelope)
def list_goals(
    db: DbDep,
    current_user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
    month: str | None = Query(None),
):
    """List user goals, optionally filtered by status and/or month."""
    result = service.list_goals(db, current_user.id, status_filter, month)
    return Envelope(data=result)


@router.get("/{goal_id}", response_model=Envelope)
def get_goal(
    goal_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Get a specific goal by ID."""
    result = service.get_goal(db, goal_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Envelope(data=result)


@router.patch("/{goal_id}", response_model=Envelope)
def update_goal(
    goal_id: int,
    data: GoalUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Update goal fields (title, subtitle, acts_target)."""
    result = service.update_goal(
        db,
        goal_id,
        current_user.id,
        title=data.title,
        subtitle=data.subtitle,
        acts_target=data.acts_target,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Envelope(data=result)


@router.patch("/{goal_id}/progress", response_model=Envelope)
def update_goal_progress(
    goal_id: int,
    data: GoalProgressUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Update goal progress (acts_done)."""
    result = service.update_progress(db, goal_id, current_user.id, data.acts_done)
    if result is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Envelope(data=result)


@router.patch("/{goal_id}/status", response_model=Envelope)
def update_goal_status(
    goal_id: int,
    data: GoalStatusUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Update goal status (active, completed, archived, replaced)."""
    result = service.update_status(db, goal_id, current_user.id, data.status)
    if result is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Envelope(data=result)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Soft-delete a goal."""
    deleted = service.delete_goal(db, goal_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")


# ---------------------------------------------------------------------------
# Monthly Reviews
# ---------------------------------------------------------------------------


@router.get("/reviews/check", response_model=Envelope)
def check_monthly_review(
    db: DbDep,
    current_user: CurrentUser,
):
    """Check if a monthly goal review is due."""
    result = service.check_review_due(db, current_user.id)
    return Envelope(data=result)


@router.post("/reviews", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def submit_monthly_review(
    data: MonthlyReviewCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    """Submit a monthly goal review."""
    try:
        result = service.submit_review(db, current_user.id, data)
        return Envelope(data=result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
