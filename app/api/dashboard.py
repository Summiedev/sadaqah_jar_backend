from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.auth import get_current_user
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/heatmap")
def get_heatmap(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id

    logs = (
    db.query(SadaqahLog.date, func.count(SadaqahLog.id))
    .filter(SadaqahLog.user_id == user_id)
    .group_by(SadaqahLog.date)
    .all()
)

    heatmap = {}

    for log in logs:
        date_str = str(log.date)
        heatmap[date_str] = heatmap.get(date_str, 0) + 1

    return heatmap