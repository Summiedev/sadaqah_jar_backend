from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.models.donation_intent import DonationIntent
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User


router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


def _enforce_admin_rate_limit(admin, limit: int = 10, period: int = 60):
    if not check_rate_limit(admin.id, limit=limit, period=period):
        raise HTTPException(status_code=429, detail="Too many requests")


@router.get("/daily-users")
def daily_users(db: Session = Depends(get_db), admin = Depends(require_admin)):
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
def top_acts(db: Session = Depends(get_db), admin = Depends(require_admin)):
    _enforce_admin_rate_limit(admin)
    results = (
        db.query(SadaqahLog.act_id, func.count(SadaqahLog.id).label("count"))
        .group_by(SadaqahLog.act_id)
        .order_by(func.count(SadaqahLog.id).desc())
        .limit(5)
        .all()
    )

    return [
        {"act_id": act_id, "count": count}
        for act_id, count in results
    ]


@router.get("/stars-today")
def stars_today(db: Session = Depends(get_db), admin = Depends(require_admin)):
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
def donation_intents(db: Session = Depends(get_db), admin = Depends(require_admin)):
    _enforce_admin_rate_limit(admin)
    results = (
        db.query(DonationIntent.charity_id, func.count(DonationIntent.id))
        .group_by(DonationIntent.charity_id)
        .all()
    )

    return [
        {"charity_id": charity_id, "count": count}
        for charity_id, count in results
    ]