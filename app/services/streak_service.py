# app/services/streak_service.py
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from app.models.user_streak import UserStreak

def update_streak(db: Session, user_id: int) -> UserStreak:
    today = date.today()
    yesterday = today - timedelta(days=1)

    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
    if not streak:
        streak = UserStreak(user_id=user_id, current_streak=1, longest_streak=1, last_completed_date=today)
        db.add(streak)
        db.commit()
        db.refresh(streak)
        return streak

    if streak.last_completed_date == today:
        return streak

    if streak.last_completed_date == yesterday:
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.last_completed_date = today
    db.commit()
    db.refresh(streak)
    return streak

def validate_streak(db: Session, user_id: int):
    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
    if not streak or not streak.last_completed_date:
        return

    today = datetime.utcnow().date()
    days_missed = (today - streak.last_completed_date).days
    if days_missed > 1:
        streak.current_streak = 0
        db.commit()