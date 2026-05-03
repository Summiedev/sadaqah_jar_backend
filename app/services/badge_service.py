from sqlalchemy.orm import Session

from app.models.badge import Badge
from app.models.user_badge import UserBadge
from app.services.leaderboard_service import get_user_rank_global


def give_user_badge(db: Session, user_id: int, badge_name: str):
    badge = db.query(Badge).filter(Badge.name == badge_name).first()
    if not badge:
        badge = Badge(name=badge_name)
        db.add(badge)
        db.commit()
        db.refresh(badge)

    exists = db.query(UserBadge).filter(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id).first()
    if exists:
        return

    user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(user_badge)
    db.commit()

def check_and_award_badges(db, user_id):
    rank_data = get_user_rank_global(user_id)
    if not rank_data:
        return
    rank = rank_data["rank"]
    if rank and rank <= 10:
        give_user_badge(db, user_id, "Top 10 Global")
    if rank == 1:
        give_user_badge(db, user_id, "Global Champion")