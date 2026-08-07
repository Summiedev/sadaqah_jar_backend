"""Sadaqah domain service layer.

All business logic for activity tracking lives here.
Routers are thin — they parse requests, call services, and return responses.

Event-driven design
-------------------
Service methods publish domain events so other domains (notifications, family,
journey, analytics) can react without tight coupling.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, event_bus
from app.sadaqah import repository as repo
from app.sadaqah.exceptions import (
    ActivityCompletionNotFoundException,
    ActivitySessionNotFoundException,
)
from app.sadaqah.models import (
    ActivityCompletion,
    ActivityContext,
    ActivityStreak,
    ActivityType,
)
from app.sadaqah.schemas import (
    ActivityCompletionResponse,
    ActivityCompletionsPage,
    ActivitySessionResponse,
    ActivitySessionsPage,
    ActivityStreakResponse,
)
from app.sadaqah.validators import validate_duration_seconds, validate_note


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today() -> date:
    return _utcnow().date()


def _is_friday(d: date) -> bool:
    return d.weekday() == 4


def _is_ramadan(d: date) -> bool:
    from app.services.hijri_service import is_ramadan as hijri_is_ramadan

    return hijri_is_ramadan(d)


def _calculate_stars(
    activity_type: ActivityType, completed_at: date
) -> tuple[int, bool, bool]:
    """Calculate stars earned for an activity completion."""
    stars = 1
    friday_boost = _is_friday(completed_at)
    ramadan_bonus = False

    if friday_boost:
        stars *= 2

    if _is_ramadan(completed_at):
        ramadan_bonus = True
        if activity_type == ActivityType.DHIKR:
            stars *= 3
        elif activity_type == ActivityType.PRAYER:
            stars *= 3
        else:
            stars *= 2

    return stars, friday_boost, ramadan_bonus


def _compute_streak(completion_dates: list[date]) -> tuple[int, int, Optional[date]]:
    """Compute current and longest streak from sorted completion dates.

    Returns (current_streak, longest_streak, last_completed_at).
    """
    if not completion_dates:
        return 0, 0, None

    # Deduplicate and sort
    unique_dates = sorted(set(completion_dates))

    # Find longest streak
    longest = 1
    longest_current = 1
    for i in range(1, len(unique_dates)):
        if (unique_dates[i] - unique_dates[i - 1]).days == 1:
            longest_current += 1
        else:
            longest = max(longest, longest_current)
            longest_current = 1
    longest = max(longest, longest_current)

    # Find current streak (ending today or yesterday)
    today = _today()
    yesterday = today - timedelta(days=1)

    current = 0
    last_completed = None

    # Walk backwards from most recent
    for i in range(len(unique_dates) - 1, -1, -1):
        d = unique_dates[i]
        if d == today or d == yesterday:
            if current == 0:
                last_completed = d
                current = 1
                yesterday = d - timedelta(days=1)
            elif (last_completed - d).days == 1:
                current += 1
                last_completed = d
                yesterday = d - timedelta(days=1)
            else:
                break
        else:
            break

    return current, longest, last_completed


# ---------------------------------------------------------------------------
# Activity Completions
# ---------------------------------------------------------------------------


def create_completion(
    db: Session,
    user_id: int,
    payload: dict,
) -> ActivityCompletionResponse:
    """Create a new activity completion."""
    activity_type = payload["activity_type"]
    context = payload.get("context", ActivityContext.PERSONAL)
    note = validate_note(payload.get("note"))
    family_id = payload.get("family_id")
    completed_at = payload.get("completed_at") or _utcnow()

    # Validate context-specific requirements
    if context in (ActivityContext.FAMILY, ActivityContext.BOTH) and not family_id:
        raise ValueError("family_id is required for family/both context")

    # Calculate stars
    stars, friday_boost, ramadan_bonus = _calculate_stars(
        activity_type,
        completed_at.date() if isinstance(completed_at, datetime) else completed_at,
    )

    completion = repo.ActivityCompletionRepository().create(
        db,
        {
            "user_id": user_id,
            "activity_type": activity_type,
            "context": context,
            "note": note,
            "family_id": family_id,
            "completed_at": completed_at,
            "stars_earned": stars,
            "friday_boost": friday_boost,
            "ramadan_bonus": ramadan_bonus,
        },
    )

    # Update streak
    _update_streak(db, user_id, activity_type, completed_at)

    # Publish event
    event_bus.publish(
        DomainEvent(
            event_type="activity.completed",
            domain="sadaqah",
            payload={
                "completion_id": completion.id,
                "user_id": user_id,
                "activity_type": activity_type.value,
                "context": context.value,
                "family_id": family_id,
                "stars_earned": stars,
                "completed_at": completion.completed_at.isoformat(),
            },
        )
    )

    return ActivityCompletionResponse(
        id=completion.id,
        user_id=completion.user_id,
        activity_type=completion.activity_type,
        context=completion.context,
        note=completion.note,
        family_id=completion.family_id,
        completed_at=completion.completed_at,
        created_at=completion.created_at,
        stars_earned=completion.stars_earned,
        friday_boost=completion.friday_boost,
        ramadan_bonus=completion.ramadan_bonus,
    )


def get_completion(
    db: Session, completion_id: int, user_id: int
) -> ActivityCompletionResponse:
    completion = repo.ActivityCompletionRepository().get(db, completion_id, user_id)
    if not completion:
        raise ActivityCompletionNotFoundException()
    return ActivityCompletionResponse(
        id=completion.id,
        user_id=completion.user_id,
        activity_type=completion.activity_type,
        context=completion.context,
        note=completion.note,
        family_id=completion.family_id,
        completed_at=completion.completed_at,
        created_at=completion.created_at,
        stars_earned=completion.stars_earned,
        friday_boost=completion.friday_boost,
        ramadan_bonus=completion.ramadan_bonus,
    )


def list_completions(
    db: Session,
    user_id: int,
    activity_type: Optional[ActivityType] = None,
    context: Optional[ActivityContext] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> ActivityCompletionsPage:
    rows, total = repo.ActivityCompletionRepository().list(
        db,
        user_id,
        activity_type=activity_type,
        context=context,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return ActivityCompletionsPage(
        data=[
            ActivityCompletionResponse(
                id=c.id,
                user_id=c.user_id,
                activity_type=c.activity_type,
                context=c.context,
                note=c.note,
                family_id=c.family_id,
                completed_at=c.completed_at,
                created_at=c.created_at,
                stars_earned=c.stars_earned,
                friday_boost=c.friday_boost,
                ramadan_bonus=c.ramadan_bonus,
            )
            for c in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Activity Sessions
# ---------------------------------------------------------------------------


def start_session(db: Session, user_id: int, payload: dict) -> ActivitySessionResponse:
    activity_type = payload["activity_type"]
    context = payload.get("context", ActivityContext.PERSONAL)
    note = validate_note(payload.get("note"))
    family_id = payload.get("family_id")
    started_at = payload.get("started_at") or _utcnow()

    if context in (ActivityContext.FAMILY, ActivityContext.BOTH) and not family_id:
        raise ValueError("family_id is required for family/both context")

    # End any existing in-progress session for this activity type
    existing = repo.ActivitySessionRepository().get_in_progress(
        db, user_id, activity_type
    )
    if existing:
        existing.ended_at = started_at
        existing.duration_seconds = int(
            (started_at - existing.started_at).total_seconds()
        )

    session = repo.ActivitySessionRepository().create(
        db,
        {
            "user_id": user_id,
            "activity_type": activity_type,
            "context": context,
            "note": note,
            "started_at": started_at,
            "family_id": family_id,
        },
    )

    event_bus.publish(
        DomainEvent(
            event_type="activity.session.started",
            domain="sadaqah",
            payload={
                "session_id": session.id,
                "user_id": user_id,
                "activity_type": activity_type.value,
                "context": context.value,
                "started_at": session.started_at.isoformat(),
            },
        )
    )

    return ActivitySessionResponse(
        id=session.id,
        user_id=session.user_id,
        activity_type=session.activity_type,
        context=session.context,
        note=session.note,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_seconds=session.duration_seconds,
        family_id=session.family_id,
        created_at=session.created_at,
    )


def end_session(
    db: Session, session_id: int, user_id: int, duration_seconds: Optional[int] = None
) -> ActivitySessionResponse:
    session = repo.ActivitySessionRepository().get(db, session_id, user_id)
    if not session:
        raise ActivitySessionNotFoundException()

    if session.ended_at is not None:
        raise ValueError("Session already ended")

    ended_at = _utcnow()
    if duration_seconds is not None:
        validate_duration_seconds(duration_seconds)
    else:
        duration_seconds = int((ended_at - session.started_at).total_seconds())

    session.ended_at = ended_at
    session.duration_seconds = duration_seconds
    db.flush()
    db.refresh(session)

    event_bus.publish(
        DomainEvent(
            event_type="activity.session.ended",
            domain="sadaqah",
            payload={
                "session_id": session.id,
                "user_id": user_id,
                "activity_type": session.activity_type.value,
                "duration_seconds": duration_seconds,
                "ended_at": ended_at.isoformat(),
            },
        )
    )

    return ActivitySessionResponse(
        id=session.id,
        user_id=session.user_id,
        activity_type=session.activity_type,
        context=session.context,
        note=session.note,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_seconds=session.duration_seconds,
        family_id=session.family_id,
        created_at=session.created_at,
    )


def list_sessions(
    db: Session,
    user_id: int,
    activity_type: Optional[ActivityType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> ActivitySessionsPage:
    rows, total = repo.ActivitySessionRepository().list(
        db,
        user_id,
        activity_type=activity_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return ActivitySessionsPage(
        data=[
            ActivitySessionResponse(
                id=s.id,
                user_id=s.user_id,
                activity_type=s.activity_type,
                context=s.context,
                note=s.note,
                started_at=s.started_at,
                ended_at=s.ended_at,
                duration_seconds=s.duration_seconds,
                family_id=s.family_id,
                created_at=s.created_at,
            )
            for s in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------


def _update_streak(
    db: Session, user_id: int, activity_type: ActivityType, completed_at: datetime
) -> ActivityStreak:
    """Update streak after a completion."""
    # Get all completion dates for this user/type
    completions = db.scalars(
        select(ActivityCompletion.completed_at).where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.activity_type == activity_type,
            ActivityCompletion.deleted_at.is_(None),
            ActivityCompletion.completed_at <= _utcnow(),
        )
    ).all()

    completion_dates = [c.date() if isinstance(c, datetime) else c for c in completions]
    current, longest, last_completed = _compute_streak(completion_dates)

    streak = repo.ActivityStreakRepository().get_or_create(db, user_id, activity_type)
    repo.ActivityStreakRepository().update(
        db,
        streak,
        {
            "current_streak": current,
            "longest_streak": max(streak.longest_streak, longest),
            "last_completed_at": last_completed,
        },
    )
    return streak


def get_streak(
    db: Session, user_id: int, activity_type: ActivityType
) -> ActivityStreakResponse:
    streak = repo.ActivityStreakRepository().get(db, user_id, activity_type)
    if not streak:
        streak = repo.ActivityStreakRepository().get_or_create(
            db, user_id, activity_type
        )
    return ActivityStreakResponse(
        id=streak.id,
        activity_type=streak.activity_type,
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_completed_at=streak.last_completed_at,
        created_at=streak.created_at,
        updated_at=streak.updated_at,
    )


def list_streaks(db: Session, user_id: int) -> list[ActivityStreakResponse]:
    streaks = repo.ActivityStreakRepository().list_for_user(db, user_id)
    return [
        ActivityStreakResponse(
            id=s.id,
            activity_type=s.activity_type,
            current_streak=s.current_streak,
            longest_streak=s.longest_streak,
            last_completed_at=s.last_completed_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in streaks
    ]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def get_summary(db: Session, user_id: int) -> dict:
    """Get activity summary for dashboard."""
    today = _today()
    thirty_days_ago = today - timedelta(days=30)

    completions, total = repo.ActivityCompletionRepository().list(
        db, user_id, start_date=thirty_days_ago, limit=1, offset=0
    )

    # Count by type
    type_counts = repo.ActivityCompletionRepository().count_by_type(
        db, user_id, start_date=thirty_days_ago
    )
    most_common = max(type_counts, key=type_counts.get) if type_counts else None

    # Friday and Ramadan counts
    thirty_days = (
        db.scalar(
            select(func.count(ActivityCompletion.id)).where(
                ActivityCompletion.user_id == user_id,
                ActivityCompletion.completed_at >= thirty_days_ago,
                ActivityCompletion.deleted_at.is_(None),
                ActivityCompletion.friday_boost,
            )
        )
        or 0
    )

    ramadan_count = (
        db.scalar(
            select(func.count(ActivityCompletion.id)).where(
                ActivityCompletion.user_id == user_id,
                ActivityCompletion.completed_at >= thirty_days_ago,
                ActivityCompletion.deleted_at.is_(None),
                ActivityCompletion.ramadan_bonus,
            )
        )
        or 0
    )

    # Total stars
    total_stars = (
        db.scalar(
            select(func.sum(ActivityCompletion.stars_earned)).where(
                ActivityCompletion.user_id == user_id,
                ActivityCompletion.deleted_at.is_(None),
            )
        )
        or 0
    )

    # Current streak across all activity types
    streaks = repo.ActivityStreakRepository().list_for_user(db, user_id)
    current_streak = max((s.current_streak for s in streaks), default=0)
    longest_streak = max((s.longest_streak for s in streaks), default=0)

    return {
        "total_completions": total,
        "total_stars_earned": int(total_stars),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "most_common_activity": most_common,
        "friday_boost_count": thirty_days,
        "ramadan_bonus_count": ramadan_count,
    }


def get_heatmap(db: Session, user_id: int, days: int = 365) -> dict[str, int]:
    """Get activity heatmap data for the last N days."""
    end_date = _today()
    start_date = end_date - timedelta(days=days)

    completions = db.scalars(
        select(ActivityCompletion.completed_at).where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.completed_at >= start_date,
            ActivityCompletion.completed_at <= end_date + timedelta(days=1),
            ActivityCompletion.deleted_at.is_(None),
        )
    ).all()

    result: dict[str, int] = {}
    for c in completions:
        d = c.date() if isinstance(c, datetime) else c
        key = d.isoformat()
        result[key] = result.get(key, 0) + 1

    return result


def get_category_breakdown(db: Session, user_id: int, days: int = 30) -> list[dict]:
    """Get activity breakdown by category for the last N days."""
    end_date = _today()
    start_date = end_date - timedelta(days=days)

    rows = db.execute(
        select(
            ActivityCompletion.activity_type,
            func.count(ActivityCompletion.id).label("count"),
            func.sum(ActivityCompletion.stars_earned).label("stars"),
        )
        .where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.completed_at >= start_date,
            ActivityCompletion.completed_at <= end_date + timedelta(days=1),
            ActivityCompletion.deleted_at.is_(None),
        )
        .group_by(ActivityCompletion.activity_type)
    ).all()

    return [
        {
            "category": str(row[0].value),
            "count": row[1],
            "stars": int(row[2] or 0),
        }
        for row in rows
    ]
