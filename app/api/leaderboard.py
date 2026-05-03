from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.auth import get_current_user
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User
from app.models.user_streak import UserStreak
from app.core.cache import get_cached_user_streak
from app.services.leaderboard_service import get_top_friday, get_user_rank_ramadan
from app.services.leaderboard_service import get_user_rank_global

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

RAMADAN_START = date(2026, 2, 17)
RAMADAN_END = date(2026, 3, 18)

@router.get("/me")
def my_rank(current_user: User = Depends(get_current_user)):
    user_id = current_user.id
    global_data = get_user_rank_global(user_id)
    ramadan_data = get_user_rank_ramadan(user_id)

    return {
        "global": global_data,
        "ramadan": ramadan_data
    }
    
@router.get("/friday")
def friday_leaderboard(limit: int = 10):
    data = get_top_friday(limit)

    return [
        {"user_id": int(uid), "stars": int(score)}
        for uid, score in data
    ]
    
@router.get("/leaderboard/ramadan")
def ramadan_leaderboard(db: Session = Depends(get_db)):
    

    results = (
        db.query(
            SadaqahLog.user_id,
            func.sum(SadaqahLog.stars_earned).label("total")
        )
        .filter(SadaqahLog.date >= RAMADAN_START)
        .filter(SadaqahLog.date <= RAMADAN_END)
        .group_by(SadaqahLog.user_id)
        .order_by(desc("total"))
        .limit(20)
        .all()
    )

    return results