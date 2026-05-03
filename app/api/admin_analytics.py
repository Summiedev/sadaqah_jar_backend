from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.donation_intent import DonationIntent
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User


router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get("/daily-users")
def daily_users(db: Session = Depends(get_db), admin = Depends(require_admin)):
    today = datetime.now(timezone.utc).date()

    count = (
        db.query(User)
        .filter(func.date(User.created_at) == today)
        .count()
    )

    return {"new_users_today": count}


@router.get("/top-acts")
def top_acts(db: Session = Depends(get_db), admin = Depends(require_admin)):
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
    today = datetime.now(timezone.utc).date()

    total = (
        db.query(func.sum(SadaqahLog.stars_earned))
        .filter(func.date(SadaqahLog.created_at) == today)
        .scalar()
    )

    return {"stars_today": total or 0}


@router.get("/donation-intents")
def donation_intents(db: Session = Depends(get_db), admin = Depends(require_admin)):
    results = (
        db.query(DonationIntent.charity_id, func.count(DonationIntent.id))
        .group_by(DonationIntent.charity_id)
        .all()
    )

    return [
        {"charity_id": charity_id, "count": count}
        for charity_id, count in results
    ]