import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit_key
from app.db.session import get_db
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User

router = APIRouter(prefix="/friday", tags=["Friday Boost"])

# Static list — 5 recommendations that rarely need changing.
# No DB table needed; this avoids a migration + admin CRUD for content
# that won't meaningfully benefit from runtime editing.
_FRIDAY_RECOMMENDATIONS = [
    {
        "id": 1,
        "title": "Send abundant salawat upon the Prophet",
        "text": "Increase your blessings upon Prophet Muhammad (PBUH) on Friday — your salawat are presented to him.",
        "source": "Sunan Abi Dawud 1531",
    },
    {
        "id": 2,
        "title": "Read Surah Al-Kahf",
        "text": "Recite Surah Al-Kahf (Quran 18) on Friday. It is a light between the two Fridays and a protection.",
        "source": "Sahih al-Bukhari, Book 60, Hadith 5 (tradition of reciting on Friday)",
    },
    {
        "id": 3,
        "title": "Give charity on Friday",
        "text": "Friday charity is multiplied. Even a small amount given sincerely on Jumu'ah carries extra weight.",
        "source": "General principle — good deeds are multiplied on blessed days",
    },
    {
        "id": 4,
        "title": "Make dua in the last hour of Asr",
        "text": "There is an hour on Friday when no Muslim asks Allah for something except that He grants it — seek it in the last hour after Asr.",
        "source": "Sahih al-Bukhari 935, Sahih Muslim 852",
    },
    {
        "id": 5,
        "title": "Reach out to family or relatives",
        "text": "Friday is a day of community. Call, text, or visit a relative to strengthen family ties.",
        "source": "General Islamic value — maintaining family ties is a command from Allah (Quran 4:1)",
    },
]


def _enforce_public_rate_limit(request: Request, limit: int = 20, period: int = 60):
    client_host = request.client.host if request.client else "unknown"
    if not check_rate_limit_key(f"friday:{client_host}", limit=limit, period=period):
        raise HTTPException(status_code=429, detail="Too many requests")


@router.get("/recommendations")
def friday_recommendations(
    current_user: User = Depends(get_current_user),
):
    """Return Friday-specific recommendations.

    The list is ordered by salawat, Kahf, charity, dua, family —
    the traditional Friday priority. No randomization; the sequence
    itself is meaningful.
    """
    return _FRIDAY_RECOMMENDATIONS


@router.get("/stats")
def friday_stats(request: Request, db: Session = Depends(get_db)):
    _enforce_public_rate_limit(request)
    today = datetime.utcnow().date()
    day_start = datetime.combine(today, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    total_stars = (
        db.query(func.sum(SadaqahLog.stars_earned))
        .filter(SadaqahLog.created_at >= day_start)
        .filter(SadaqahLog.created_at < day_end)
        .scalar()
    )

    total_users = (
        db.query(func.count(func.distinct(SadaqahLog.user_id)))
        .filter(SadaqahLog.created_at >= day_start)
        .filter(SadaqahLog.created_at < day_end)
        .scalar()
    )

    return {
        "friday_stars": total_stars or 0,
        "active_users": total_users or 0
    }
