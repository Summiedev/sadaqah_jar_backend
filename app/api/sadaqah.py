from datetime import datetime
from fastapi import HTTPException
import random

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.db.deps import get_db
from app.models.user import User
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog

from app.core.auth import get_current_user
from app.core.cache import cache_daily_acts, get_cached_daily_acts
from app.core.ws_manager import manager

from app.services.streak_service import update_streak
from app.services.badge_service import check_and_award_badges

from app.services.jumua_service import is_friday
from app.services.ramadan_service import is_ramadan, is_last_10_nights
from app.services.leaderboard_service import increment_friday, increment_global, increment_ramadan, increment_weekly

from app.tasks.scheduled_tasks import jar_completion_celebration

router = APIRouter(prefix="/sadaqah", tags=["sadaqah"])

@router.get("/daily")
def get_daily_acts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user_id = current_user.id

    cached = get_cached_daily_acts(user_id)
    if cached:
        return cached

    if is_ramadan():
        acts = (
            db.query(SadaqahAct)
            .filter(SadaqahAct.verified == True)
            .order_by(func.random())
            .limit(20)
            .all()
        )
    else:
        acts = (
            db.query(SadaqahAct)
            .filter(
                SadaqahAct.verified == True,
                SadaqahAct.is_ramadan_only == False
            )
            .order_by(func.random())
            .limit(20)
            .all()
        )

    daily = random.sample(acts, min(5, len(acts)))

    response = [
        {
            "id": act.id,
            "title": act.title,
            "category": act.category,
            "difficulty": act.difficulty
        }
        for act in daily
    ]

    cache_daily_acts(user_id, response)

    return response

@router.post("/jar/add-star")
async def add_star(act_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if act_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid act ID")
    
    user_id = current_user.id

    # Rate limit (raise HTTP 429 if exceeded)
    if not check_rate_limit(user_id, limit=5, period=60):
        raise HTTPException(status_code=429, detail="Too many requests")

    jar = db.query(Jar).filter(Jar.user_id == user_id, Jar.completed_at.is_(None)).first()
    if not jar:
        jar = Jar(user_id=user_id)
        db.add(jar)
        db.commit()
        db.refresh(jar)

    today = datetime.utcnow().date()

    existing = db.query(SadaqahLog).filter(
        SadaqahLog.user_id == user_id,
        SadaqahLog.act_id == act_id,
        SadaqahLog.date == today
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already added today")

    act = db.query(SadaqahAct).filter(SadaqahAct.id == act_id, SadaqahAct.verified == True).first()
    if not act:
        raise HTTPException(status_code=404, detail="Act not found")

    multiplier = act.reward_weight or 1
    friday = is_friday()
    ramadan = is_ramadan(today)
    last10 = is_last_10_nights(today)

    if friday:
        multiplier *= 2
    if ramadan:
        multiplier *= act.ramadan_multiplier
    if last10:
        multiplier *= 2

    # Create log BEFORE leaderboard so analytics reflect DB state
    log = SadaqahLog(
        user_id=user_id,
        act_id=act_id,
        date=today,
        created_at=datetime.utcnow(),
        stars_earned=multiplier,
        friday_boost=friday,
        ramadan_bonus=ramadan
    )
    db.add(log)

    jar.current_stars += multiplier
    if jar.current_stars >= jar.capacity:
        jar.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(jar)

    # Update leaderboards (Redis)
    increment_global(user_id, multiplier)
    increment_weekly(user_id, multiplier)
    if ramadan:
        increment_ramadan(user_id, multiplier)
    if friday:
        increment_friday(user_id, multiplier)

    # Award badges (after leaderboards updated)
  
    check_and_award_badges(db, user_id)

    # Update streak
    streak = update_streak(db, user_id)

    # WebSocket update (send_user_event)
    try:
        await manager.send_user_event(user_id, {
            "event": "jar_update",
            "current_stars": jar.current_stars,
            "capacity": jar.capacity,
            "streak": {"current": streak.current_streak, "longest": streak.longest_streak}
        })
    except Exception:
        # swallow websocket errors, don't break API response
        pass

    # If jar completed, schedule celebration
    if jar.completed_at:
        from app.tasks.scheduled_tasks import jar_completion_celebration
        jar_completion_celebration.delay(jar.id)

    return {"current_stars": jar.current_stars, "capacity": jar.capacity, "completed_at": jar.completed_at}
@router.get("/jar")
def get_jar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user_id = current_user.id

    jar = db.query(Jar).filter(
        Jar.user_id == user_id,
        Jar.completed_at.is_(None)
    ).first()

    if not jar:
        return {"current_stars": 0, "capacity": 33}

    return {
        "current_stars": jar.current_stars,
        "capacity": jar.capacity,
        "completed_at": jar.completed_at
    }