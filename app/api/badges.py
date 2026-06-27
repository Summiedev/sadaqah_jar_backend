from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.services.badge_service import get_badge_progress, get_earned_badges

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("/me")
def my_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    earned = get_earned_badges(db, current_user.id)
    progress = get_badge_progress(db, current_user.id)
    return {"earned": earned, "next_up": progress}