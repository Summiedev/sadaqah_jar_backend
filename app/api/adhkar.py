from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.adhkar import Adhkar, TimeOfDay
from app.models.user import User

router = APIRouter(prefix="/adhkar", tags=["adhkar"])


def _daily_adhkar(db: Session, time_of_day: TimeOfDay, user_id: int, limit: int):
    query = db.query(Adhkar).filter(Adhkar.time_of_day == time_of_day)
    total = query.count()
    if total == 0:
        return []
    offset = (date.today().toordinal() + user_id) % total
    rows = query.order_by(Adhkar.id.asc()).offset(offset).limit(limit).all()
    if len(rows) < limit and offset:
        rows.extend(query.order_by(Adhkar.id.asc()).limit(limit - len(rows)).all())
    return rows


@router.get("/morning")
def get_morning_adhkar(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return random morning adhkar entries, ordered randomly.
    The randomization ensures users see variety day-to-day.
    """
    rows = _daily_adhkar(db, TimeOfDay.morning, current_user.id, limit)

    return [
        {
            "id": row.id,
            "text_arabic": row.text_arabic,
            "text_translation": row.text_translation,
            "source": row.source,
            "repeat_count": row.repeat_count,
        }
        for row in rows
    ]


@router.get("/evening")
def get_evening_adhkar(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return random evening adhkar entries, ordered randomly.
    Mirrors get_morning_adhkar but filters by TimeOfDay.evening.
    """
    rows = _daily_adhkar(db, TimeOfDay.evening, current_user.id, limit)

    return [
        {
            "id": row.id,
            "text_arabic": row.text_arabic,
            "text_translation": row.text_translation,
            "source": row.source,
            "repeat_count": row.repeat_count,
        }
        for row in rows
    ]
