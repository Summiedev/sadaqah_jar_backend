from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.user_streak import UserStreak
from app.core.cache import get_cached_user_streak

router = APIRouter(prefix="/streak", tags=["streak"])


@router.get("/streak")
def get_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id

    cached = get_cached_user_streak(user_id)
    if cached:
        return {"source": "cache", **cached}

    streak = db.query(UserStreak).filter(
        UserStreak.user_id == user_id
    ).first()

    if not streak:
        return {
            "current_streak": 0,
            "longest_streak": 0
        }

    return {
        "source": "database",
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak
    }