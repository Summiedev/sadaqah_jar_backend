from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit, check_rate_limit_key
from app.db.deps import get_db
from app.core.auth import get_current_user
from app.services.leaderboard_service import get_top_global
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User
from app.models.user_streak import UserStreak
from app.core.cache import get_cached_user_streak
from app.services.leaderboard_service import get_top_friday, get_user_rank_ramadan
from app.services.leaderboard_service import get_user_rank_global
from app.models.leaderboard_season import LeaderboardSeason

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _ramadan_season(db: Session, today: date | None = None) -> LeaderboardSeason | None:
    today = today or _utc_today()
    return (
        db.query(LeaderboardSeason)
        .filter(func.lower(LeaderboardSeason.season_name) == "ramadan")
        .filter(LeaderboardSeason.start_date <= today)
        .filter(LeaderboardSeason.end_date >= today)
        .first()
    )


def _enforce_rate_limit(key: str, limit: int = 20, period: int = 60):
    if not check_rate_limit_key(key, limit=limit, period=period):
        raise HTTPException(status_code=429, detail="Too many requests")

@router.get("/me")
def my_rank(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    if not check_rate_limit(user_id, limit=20, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")
    global_data = get_user_rank_global(user_id)
    ramadan_active = _ramadan_season(db) is not None
    ramadan_data = get_user_rank_ramadan(user_id, active=ramadan_active)

    return {
        "global": global_data,
        "ramadan": ramadan_data
    }
    
@router.get("/friday")
def friday_leaderboard(request: Request, limit: int = 10):
    client_host = request.client.host if request.client else "unknown"
    _enforce_rate_limit(f"leaderboard:friday:{client_host}")
    data = get_top_friday(limit)

    return [
        {"user_id": int(uid), "stars": int(score)}
        for uid, score in data
    ]


@router.get("/global")
def global_leaderboard(request: Request, limit: int = 10):
    client_host = request.client.host if request.client else "unknown"
    _enforce_rate_limit(f"leaderboard:global:{client_host}")
    data = get_top_global(limit)
    return [
        {"user_id": int(uid), "stars": int(score)}
        for uid, score in data
    ]
    
@router.get("/ramadan")
def ramadan_leaderboard(request: Request, db: Session = Depends(get_db)):
    client_host = request.client.host if request.client else "unknown"
    _enforce_rate_limit(f"leaderboard:ramadan:{client_host}")
    season = _ramadan_season(db)
    if season is None:
        return []

    results = (
        db.query(
            SadaqahLog.user_id,
            func.sum(SadaqahLog.stars_earned).label("total")
        )
        .filter(SadaqahLog.date >= season.start_date)
        .filter(SadaqahLog.date <= season.end_date)
        .group_by(SadaqahLog.user_id)
        .order_by(desc("total"))
        .limit(20)
        .all()
    )

    return [
        {"user_id": int(uid), "stars": int(total)}
        for uid, total in results
    ]
