from datetime import datetime
from sqlalchemy import func
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.sadaqah_log import SadaqahLog

router = APIRouter(prefix="/friday", tags=["Friday Boost"])


@router.get("/leaderboard")
def friday_leaderboard(db: Session = Depends(get_db)):
    if datetime.utcnow().weekday() != 4:
        return {"message": "Friday leaderboard only available on Friday"}

    today = datetime.utcnow().date()

    results = (
        db.query(SadaqahLog.user_id, func.sum(SadaqahLog.stars_earned).label("total"))
        .filter(func.date(SadaqahLog.created_at) == today)
        .group_by(SadaqahLog.user_id)
        .order_by(func.sum(SadaqahLog.stars_earned).desc())
        .all()
    )

    return results

@router.get("/stats")
def friday_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()

    total_stars = (
        db.query(func.sum(SadaqahLog.stars_earned))
        .filter(func.date(SadaqahLog.created_at) == today)
        .scalar()
    )

    total_users = (
        db.query(func.count(func.distinct(SadaqahLog.user_id)))
        .filter(func.date(SadaqahLog.created_at) == today)
        .scalar()
    )

    return {
        "friday_stars": total_stars or 0,
        "active_users": total_users or 0
    }