from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.models.donation_intent import DonationIntent
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User
from app.books.bookmark_model import BookBookmark
from app.journey.models import (
    JourneyAdhkarProgress,
    JourneyPrayerCompletion,
    JourneyQuranProgress,
    JourneyReadingProgress,
    JourneyReflection,
)
from app.sadaqah.models import ActivityCompletion
from app.models.broadcast import BroadcastReceipt


router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


def _enforce_admin_rate_limit(admin, limit: int = 10, period: int = 60):
    if not check_rate_limit(admin.id, limit=limit, period=period):
        raise HTTPException(status_code=429, detail="Too many requests")


@router.get("/daily-users")
def daily_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    _enforce_admin_rate_limit(admin)
    today = datetime.now(timezone.utc).date()
    day_start = datetime.combine(today, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    count = (
        db.query(func.count(User.id))
        .filter(User.created_at >= day_start)
        .filter(User.created_at < day_end)
        .scalar()
    )

    return {"new_users_today": count or 0}


@router.get("/top-acts")
def top_acts(db: Session = Depends(get_db), admin=Depends(require_admin)):
    _enforce_admin_rate_limit(admin)
    results = (
        db.query(SadaqahLog.act_id, func.count(SadaqahLog.id).label("count"))
        .group_by(SadaqahLog.act_id)
        .order_by(func.count(SadaqahLog.id).desc())
        .limit(5)
        .all()
    )

    return [{"act_id": act_id, "count": count} for act_id, count in results]


@router.get("/stars-today")
def stars_today(db: Session = Depends(get_db), admin=Depends(require_admin)):
    _enforce_admin_rate_limit(admin)
    today = datetime.now(timezone.utc).date()
    day_start = datetime.combine(today, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    total = (
        db.query(func.sum(SadaqahLog.stars_earned))
        .filter(SadaqahLog.created_at >= day_start)
        .filter(SadaqahLog.created_at < day_end)
        .scalar()
    )

    return {"stars_today": total or 0}


@router.get("/donation-intents")
def donation_intents(db: Session = Depends(get_db), admin=Depends(require_admin)):
    _enforce_admin_rate_limit(admin)
    results = (
        db.query(DonationIntent.charity_id, func.count(DonationIntent.id))
        .group_by(DonationIntent.charity_id)
        .all()
    )

    return [{"charity_id": charity_id, "count": count} for charity_id, count in results]


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
    start_date: date | None = None,
    end_date: date | None = None,
):
    """Return privacy-safe aggregate metrics for the admin dashboard."""
    _enforce_admin_rate_limit(admin)
    end = end_date or datetime.now(timezone.utc).date()
    start = start_date or end - timedelta(days=30)
    if start > end:
        raise HTTPException(status_code=422, detail="Start date must be before end date")
    today_start = datetime.combine(end, datetime.min.time())
    week_start = today_start - timedelta(days=6)
    month_start = today_start - timedelta(days=29)
    range_start = datetime.combine(start, datetime.min.time())
    range_end = datetime.combine(end + timedelta(days=1), datetime.min.time())
    active_start = range_end - timedelta(days=30)

    def count(column, *, lower=None, upper=None, filters=()):
        query = db.query(func.count(column))
        if filters:
            query = query.filter(*filters)
        if lower is not None:
            query = query.filter(column >= lower)
        if upper is not None:
            query = query.filter(column < upper)
        return int(query.scalar() or 0)

    user_scope = User.deleted_at.is_(None)
    active_users = int(
        db.query(func.count(User.id))
        .filter(user_scope, User.last_active >= active_start, User.last_active < range_end)
        .scalar()
        or 0
    )
    total_users = int(db.query(func.count(User.id)).filter(user_scope).scalar() or 0)
    new_today = count(
        User.created_at,
        lower=today_start,
        upper=today_start + timedelta(days=1),
        filters=(user_scope,),
    )
    new_week = count(
        User.created_at,
        lower=week_start,
        upper=range_end,
        filters=(user_scope,),
    )
    new_month = count(
        User.created_at,
        lower=month_start,
        upper=range_end,
        filters=(user_scope,),
    )

    daily = (
        db.query(func.date(User.last_active), func.count(func.distinct(User.id)))
        .filter(
            user_scope,
            User.last_active >= range_start,
            User.last_active < range_end,
        )
        .group_by(func.date(User.last_active))
        .order_by(func.date(User.last_active))
        .all()
    )
    daily_active_today = int(
        db.query(func.count(func.distinct(User.id)))
        .filter(
            user_scope,
            User.last_active >= today_start,
            User.last_active < today_start + timedelta(days=1),
        )
        .scalar()
        or 0
    )
    returning_users = int(
        db.query(func.count(func.distinct(User.id)))
        .filter(
            user_scope,
            User.created_at < range_start,
            User.last_active >= range_start,
            User.last_active < range_end,
        )
        .scalar()
        or 0
    )
    activity_count = int(db.query(func.count(ActivityCompletion.id)).filter(
        ActivityCompletion.completed_at >= range_start,
        ActivityCompletion.completed_at < range_end,
        ActivityCompletion.deleted_at.is_(None),
    ).scalar() or 0)
    reflection_count = int(db.query(func.count(JourneyReflection.id)).filter(
        JourneyReflection.created_at >= range_start,
        JourneyReflection.created_at < range_end,
        JourneyReflection.deleted_at.is_(None),
    ).scalar() or 0)
    sadaqah_count = int(db.query(func.count(SadaqahLog.id)).filter(
        SadaqahLog.created_at >= range_start, SadaqahLog.created_at < range_end
    ).scalar() or 0)
    prayer_count = int(
        db.query(func.count(JourneyPrayerCompletion.id))
        .filter(
            JourneyPrayerCompletion.completed_at >= range_start,
            JourneyPrayerCompletion.completed_at < range_end,
        )
        .scalar()
        or 0
    )
    adhkar_count = int(
        db.query(func.count(JourneyAdhkarProgress.id))
        .filter(
            JourneyAdhkarProgress.updated_at >= range_start,
            JourneyAdhkarProgress.updated_at < range_end,
        )
        .scalar()
        or 0
    )
    quran_count = int(
        db.query(func.count(JourneyQuranProgress.id))
        .filter(
            JourneyQuranProgress.last_read_at >= range_start,
            JourneyQuranProgress.last_read_at < range_end,
        )
        .scalar()
        or 0
    )
    reading_count = int(
        db.query(func.count(JourneyReadingProgress.id))
        .filter(
            JourneyReadingProgress.last_read_at >= range_start,
            JourneyReadingProgress.last_read_at < range_end,
        )
        .scalar()
        or 0
    )
    journey_count = (
        activity_count
        + reflection_count
        + sadaqah_count
        + prayer_count
        + adhkar_count
        + quran_count
        + reading_count
    )
    books_saved = int(db.query(func.count(BookBookmark.id)).filter(
        BookBookmark.created_at >= range_start, BookBookmark.created_at < range_end
    ).scalar() or 0)
    broadcast_views = int(db.query(func.count(BroadcastReceipt.viewed_at)).filter(
        BroadcastReceipt.viewed_at >= range_start, BroadcastReceipt.viewed_at < range_end
    ).scalar() or 0)
    broadcast_clicks = int(db.query(func.count(BroadcastReceipt.clicked_at)).filter(
        BroadcastReceipt.clicked_at >= range_start, BroadcastReceipt.clicked_at < range_end
    ).scalar() or 0)

    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "users": {
            "total": total_users,
            "new_today": new_today,
            "new_this_week": new_week,
            "new_this_month": new_month,
            "active_30_days": active_users,
            "daily_active": daily_active_today,
            "returning": returning_users,
            "weekly_active": int(
                db.query(func.count(func.distinct(User.id)))
                .filter(user_scope, User.last_active >= week_start, User.last_active < range_end)
                .scalar()
                or 0
            ),
            "monthly_active": int(
                db.query(func.count(func.distinct(User.id)))
                .filter(user_scope, User.last_active >= month_start, User.last_active < range_end)
                .scalar()
                or 0
            ),
        },
        "activity": {
            "completions": activity_count,
            "reflections": reflection_count,
            "sadaqah_records": sadaqah_count,
            "journey_events": journey_count,
            "books_saved": books_saved,
            "donation_intents": int(db.query(func.count(DonationIntent.id)).filter(
                DonationIntent.created_at >= range_start, DonationIntent.created_at < range_end
            ).scalar() or 0),
            "broadcast_views": broadcast_views,
            "broadcast_clicks": broadcast_clicks,
        },
        "daily_active_users": [{"date": str(day), "count": int(value)} for day, value in daily],
    }
