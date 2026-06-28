from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.badge import Badge
from app.models.jar import Jar
from app.models.user_badge import UserBadge
from app.models.user_streak import UserStreak
from app.services.leaderboard_service import get_user_rank_global

# Badge thresholds per category
STREAK_BADGES = [(7, "7-Day Streak"), (30, "30-Day Streak"), (100, "100-Day Streak")]
JAR_BADGES = [
    (1, "First Jar Completed"),
    (5, "5 Jars Completed"),
    (10, "10 Jars Completed"),
]


def give_user_badge(db: Session, user_id: int, badge_name: str, commit: bool = True):
    badge = db.query(Badge).filter(Badge.name == badge_name).first()
    if not badge:
        badge = Badge(name=badge_name, description=badge_name)
        db.add(badge)
        db.flush()
        if commit:
            db.commit()
        db.refresh(badge)

    exists = (
        db.query(UserBadge)
        .filter(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id)
        .first()
    )
    if exists:
        return

    user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(user_badge)
    db.flush()
    if commit:
        db.commit()


def _check_streak_badges(db: Session, user_id: int, commit: bool = True):
    streak = (
        db.query(UserStreak.current_streak)
        .filter(UserStreak.user_id == user_id)
        .scalar()
    )
    if not streak:
        return
    for threshold, name in STREAK_BADGES:
        if streak >= threshold:
            give_user_badge(db, user_id, name, commit=commit)


def _check_jar_badges(db: Session, user_id: int, commit: bool = True):
    count = (
        db.query(func.count(Jar.id))
        .filter(Jar.user_id == user_id, Jar.completed_at.isnot(None))
        .scalar()
    ) or 0
    for threshold, name in JAR_BADGES:
        if count >= threshold:
            give_user_badge(db, user_id, name, commit=commit)


def check_and_award_badges(db, user_id: int, commit: bool = True):
    # Rank badges (existing)
    try:
        rank_data = get_user_rank_global(user_id)
    except Exception:
        rank_data = None
    if rank_data:
        rank = rank_data["rank"]
        if rank and rank <= 10:
            give_user_badge(db, user_id, "Top 10 Global", commit=commit)
        if rank == 1:
            give_user_badge(db, user_id, "Global Champion", commit=commit)

    # Streak badges
    _check_streak_badges(db, user_id, commit=commit)

    # Jar completion badges
    _check_jar_badges(db, user_id, commit=commit)


def get_earned_badges(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(Badge.name, Badge.description)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .filter(UserBadge.user_id == user_id)
        .all()
    )
    return [{"name": name, "description": desc} for name, desc in rows]


def get_badge_progress(db: Session, user_id: int) -> list[dict]:
    """Return progress toward the next unearned badge in each category."""
    result = []

    # Streak progress
    current_streak = (
        db.query(UserStreak.current_streak)
        .filter(UserStreak.user_id == user_id)
        .scalar()
    ) or 0

    earned_streak_names = {
        r[0]
        for r in db.query(Badge.name)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .filter(
            UserBadge.user_id == user_id, Badge.name.in_([n for _, n in STREAK_BADGES])
        )
        .all()
    }

    for threshold, name in STREAK_BADGES:
        if name not in earned_streak_names:
            result.append(
                {
                    "category": "streak",
                    "badge": name,
                    "current": current_streak,
                    "threshold": threshold,
                    "progress": min(current_streak / threshold, 1.0),
                }
            )
            break

    # Jar progress
    jars_completed = (
        db.query(func.count(Jar.id))
        .filter(Jar.user_id == user_id, Jar.completed_at.isnot(None))
        .scalar()
    ) or 0

    earned_jar_names = {
        r[0]
        for r in db.query(Badge.name)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .filter(
            UserBadge.user_id == user_id, Badge.name.in_([n for _, n in JAR_BADGES])
        )
        .all()
    }

    for threshold, name in JAR_BADGES:
        if name not in earned_jar_names:
            result.append(
                {
                    "category": "jar",
                    "badge": name,
                    "current": jars_completed,
                    "threshold": threshold,
                    "progress": min(jars_completed / threshold, 1.0),
                }
            )
            break

    return result
