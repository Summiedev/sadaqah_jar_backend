from random import shuffle
from datetime import datetime
from app.models.sadaqah_log import SadaqahLog
from app.models.sadaqah_act import SadaqahAct
from app.services.ramadan_service import is_ramadan
from sqlalchemy.orm import Session


# app/services/personalization_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.sadaqah_log import SadaqahLog
from app.models.sadaqah_act import SadaqahAct

def get_user_behavior_profile(db: Session, user_id: int):
    # join logs to acts and aggregate
    rows = (
        db.query(SadaqahAct.category, func.count(SadaqahLog.id).label("cnt"), func.avg(SadaqahAct.difficulty).label("avg_difficulty"))
        .join(SadaqahLog, SadaqahLog.act_id == SadaqahAct.id)
        .filter(SadaqahLog.user_id == user_id)
        .group_by(SadaqahAct.category)
        .all()
    )

    category_count = {row[0]: row[1] for row in rows}
    # compute avg_difficulty overall safely
    difficulty_rows = db.query(func.avg(SadaqahAct.difficulty)).join(SadaqahLog, SadaqahLog.act_id == SadaqahAct.id).filter(SadaqahLog.user_id == user_id).scalar()
    avg_difficulty = float(difficulty_rows) if difficulty_rows else 1.0

    favorite_categories = sorted(category_count.keys(), key=lambda k: category_count[k], reverse=True)
    return {"favorite_categories": favorite_categories, "avg_difficulty": avg_difficulty}
def generate_personalized_acts(db: Session, user_id: int):
    profile = get_user_behavior_profile(db, user_id)

    base_query = db.query(SadaqahAct).filter(
        SadaqahAct.verified == True
    )

    if not is_ramadan():
        base_query = base_query.filter(
            SadaqahAct.is_ramadan_only == False
        )

    acts = base_query.all()

    # Score acts
    scored_acts = []

    for act in acts:
        score = 1

        # Favor preferred categories
        if act.category in profile["favorite_categories"][:2]:
            score += 2

        # Balance difficulty
        if act.difficulty <= profile["avg_difficulty"] + 1:
            score += 1

        # Ramadan boost
        if is_ramadan():
            score += act.ramadan_multiplier

        scored_acts.append((act, score))

    # Sort by score
    scored_acts.sort(key=lambda x: x[1], reverse=True)

    return [act for act, _ in scored_acts[:5]]