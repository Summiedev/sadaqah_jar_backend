"""Sadaqah domain router.

Thin endpoints — all business logic lives in the service layer.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.sadaqah import service
from app.sadaqah.models import ActivityContext, ActivityType
from app.sadaqah.schemas import (
    ActivityCompletionCreate,
    ActivitySessionCreate,
)


router = APIRouter(prefix="/activities", tags=["activities"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Activity Completions
# ---------------------------------------------------------------------------


@router.post("/completions", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_completion(
    payload: ActivityCompletionCreate,
    current_user: CurrentUser,
    db: DbDep,
):
    """Record a new activity completion."""
    completion = service.create_completion(
        db, current_user.id, payload.model_dump(exclude_unset=True)
    )
    return Envelope(data=completion, message="Activity recorded")


@router.get("/completions", response_model=Envelope)
def list_completions(
    current_user: CurrentUser,
    db: DbDep,
    activity_type: ActivityType | None = Query(None),
    context: ActivityContext | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List activity completions with optional filters."""
    page = service.list_completions(
        db,
        current_user.id,
        activity_type=activity_type,
        context=context,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return Envelope(
        data=page.data,
        meta=Meta(total=page.total, has_more=page.total > offset + limit),
    )


@router.get("/completions/{completion_id}", response_model=Envelope)
def get_completion(
    completion_id: int,
    current_user: CurrentUser,
    db: DbDep,
):
    """Get a specific activity completion."""
    completion = service.get_completion(db, completion_id, current_user.id)
    return Envelope(data=completion)


# ---------------------------------------------------------------------------
# Activity Sessions
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: ActivitySessionCreate,
    current_user: CurrentUser,
    db: DbDep,
):
    """Start a new activity session."""
    session = service.start_session(db, current_user.id, payload.model_dump(exclude_unset=True))
    return Envelope(data=session, message="Session started")


@router.post("/sessions/{session_id}/end", response_model=Envelope)
def end_session(
    session_id: int,
    current_user: CurrentUser,
    db: DbDep,
    duration_seconds: int | None = Query(None, ge=0),
):
    """End an active activity session."""
    session = service.end_session(db, session_id, current_user.id, duration_seconds)
    return Envelope(data=session, message="Session ended")


@router.get("/sessions", response_model=Envelope)
def list_sessions(
    current_user: CurrentUser,
    db: DbDep,
    activity_type: ActivityType | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List activity sessions with optional filters."""
    page = service.list_sessions(
        db,
        current_user.id,
        activity_type=activity_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return Envelope(
        data=page.data,
        meta=Meta(total=page.total, has_more=page.total > offset + limit),
    )


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------


@router.get("/streaks/{activity_type}", response_model=Envelope)
def get_streak(
    activity_type: ActivityType,
    current_user: CurrentUser,
    db: DbDep,
):
    """Get streak for a specific activity type."""
    streak = service.get_streak(db, current_user.id, activity_type)
    return Envelope(data=streak)


@router.get("/streaks", response_model=Envelope)
def list_streaks(
    current_user: CurrentUser,
    db: DbDep,
):
    """Get all activity streaks for the current user."""
    streaks = service.list_streaks(db, current_user.id)
    return Envelope(data=streaks)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=Envelope)
def get_summary(
    current_user: CurrentUser,
    db: DbDep,
):
    """Get activity summary for dashboard."""
    summary = service.get_summary(db, current_user.id)
    return Envelope(data=summary)


@router.get("/heatmap", response_model=Envelope)
def get_heatmap(
    current_user: CurrentUser,
    db: DbDep,
    days: int = Query(365, ge=7, le=730),
):
    """Get activity heatmap data."""
    data = service.get_heatmap(db, current_user.id, days=days)
    return Envelope(data=data)


@router.get("/categories", response_model=Envelope)
def get_category_breakdown(
    current_user: CurrentUser,
    db: DbDep,
    days: int = Query(30, ge=1, le=365),
):
    """Get activity breakdown by category."""
    data = service.get_category_breakdown(db, current_user.id, days=days)
    return Envelope(data=data)
