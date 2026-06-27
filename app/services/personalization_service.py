from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.sadaqah_log import SadaqahLog
from app.models.sadaqah_act import SadaqahAct
from app.services.ramadan_service import is_ramadan

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


def generate_personalized_acts(
    db: Session,
    user_id: int,
    acts: Sequence[SadaqahAct] | None = None,
    profile: dict | None = None,
):
    profile = profile or get_user_behavior_profile(db, user_id)
    candidate_acts = acts

    if candidate_acts is None:
        base_query = db.query(SadaqahAct).filter(
            SadaqahAct.verified == True
        )

        if not is_ramadan():
            base_query = base_query.filter(
                SadaqahAct.is_ramadan_only == False
            )

        candidate_acts = base_query.all()

    scored_acts = []
    favorite_categories = set(profile["favorite_categories"][:2])
    avg_difficulty = profile["avg_difficulty"]
    ramadan_active = is_ramadan()

    for act in candidate_acts:
        score = 1

        if act.category in favorite_categories:
            score += 2

        if act.difficulty <= avg_difficulty + 1:
            score += 1

        if ramadan_active:
            score += act.ramadan_multiplier

        scored_acts.append((act, score))

    scored_acts.sort(key=lambda x: x[1], reverse=True)

    return [act for act, _ in scored_acts[:5]]