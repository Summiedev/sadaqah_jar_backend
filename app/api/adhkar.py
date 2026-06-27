from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.adhkar import Adhkar, TimeOfDay
from app.models.user import User

router = APIRouter(prefix="/adhkar", tags=["adhkar"])


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
    rows = (
        db.query(Adhkar)
        .filter(Adhkar.time_of_day == TimeOfDay.morning)
        .order_by(func.random())
        .limit(limit)
        .all()
    )

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