from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.core.cache import (
    cache_dashboard_stats,
    cache_category_analytics,
    get_cached_dashboard_stats,
    get_cached_category_analytics,
)
from app.db.deps import get_db
from app.core.auth import get_current_user
from app.models.sadaqah_log import SadaqahLog
from app.models.sadaqah_act import SadaqahAct
from app.models.jar import Jar
from app.models.donation_intent import DonationIntent
from app.models.user import User
from app.models.user_streak import UserStreak


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/heatmap")
def get_heatmap(
    start_date: date | None = Query(None, alias="start_date"),
    end_date: date | None = Query(None, alias="end_date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id

    if not check_rate_limit(user_id, limit=30, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    # Default to trailing 365 days — bounds the response for every caller
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    logs = (
        db.query(SadaqahLog.date, func.count(SadaqahLog.id))
        .filter(
            SadaqahLog.user_id == user_id,
            SadaqahLog.date >= start_date,
            SadaqahLog.date <= end_date,
        )
        .group_by(SadaqahLog.date)
        .all()
    )

    return {str(log[0]): log[1] for log in logs}


@router.get("/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id

    if not check_rate_limit(user_id, limit=30, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    cached = get_cached_dashboard_stats(user_id)
    if cached:
        return cached

    # Single aggregation: COUNT + SUM from sadaqah_logs
    # SELECT COUNT(id), SUM(stars_earned) FROM sadaqah_logs WHERE user_id = :uid
    log_agg = (
        db.query(
            func.count(SadaqahLog.id).label("total_acts"),
            func.sum(SadaqahLog.stars_earned).label("total_stars"),
        )
        .filter(SadaqahLog.user_id == user_id)
        .one()
    )

    # SELECT COUNT(id) FROM jars WHERE user_id = :uid AND completed_at IS NOT NULL
    total_jars = (
        db.query(func.count(Jar.id))
        .filter(Jar.user_id == user_id, Jar.completed_at.isnot(None))
        .scalar()
    )

    # Single-row lookup on user_streaks (unique constraint on user_id)
    streak = (
        db.query(UserStreak.current_streak, UserStreak.longest_streak)
        .filter(UserStreak.user_id == user_id)
        .first()
    )

    # Most common category: JOIN sadaqah_logs → sadaqah_acts, GROUP BY category, ORDER BY cnt DESC LIMIT 1
    category_row = (
        db.query(SadaqahAct.category, func.count(SadaqahLog.id).label("cnt"))
        .join(SadaqahLog, SadaqahLog.act_id == SadaqahAct.id)
        .filter(SadaqahLog.user_id == user_id)
        .group_by(SadaqahAct.category)
        .order_by(func.count(SadaqahLog.id).desc())
        .first()
    )

    # SELECT COUNT(id) FROM donation_intents WHERE user_id = :uid
    donations_count = (
        db.query(func.count(DonationIntent.id))
        .filter(DonationIntent.user_id == user_id)
        .scalar()
    )

    total_acts = log_agg.total_acts or 0
    total_stars = int(log_agg.total_stars or 0)

    result = {
        "total_acts_completed": total_acts,
        "total_stars_earned": total_stars,
        "total_jars_completed": total_jars or 0,
        "current_streak": streak.current_streak if streak else 0,
        "longest_streak": streak.longest_streak if streak else 0,
        "most_common_category": str(category_row.category.value) if category_row and category_row.category else None,
        "donations_made_count": donations_count or 0,
    }

    cache_dashboard_stats(user_id, result)
    return result


@router.get("/category-analytics")
def get_category_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id

    if not check_rate_limit(user_id, limit=30, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    cached = get_cached_category_analytics(user_id)
    if cached:
        return cached

    # SELECT a.category, COUNT(l.id), SUM(l.stars_earned)
    # FROM sadaqah_logs l
    # JOIN sadaqah_acts a ON a.id = l.act_id
    # WHERE l.user_id = :uid
    # GROUP BY a.category
    # ORDER BY COUNT(l.id) DESC
    rows = (
        db.query(
            SadaqahAct.category,
            func.count(SadaqahLog.id).label("cnt"),
            func.sum(SadaqahLog.stars_earned).label("stars"),
        )
        .join(SadaqahLog, SadaqahLog.act_id == SadaqahAct.id)
        .filter(SadaqahLog.user_id == user_id)
        .group_by(SadaqahAct.category)
        .order_by(func.count(SadaqahLog.id).desc())
        .all()
    )

    result = [
        {
            "category": str(row.category.value) if hasattr(row.category, "value") else str(row.category),
            "count": row.cnt,
            "stars": int(row.stars or 0),
        }
        for row in rows
    ]

    cache_category_analytics(user_id, result)
    return result