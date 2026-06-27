from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.deps import get_db
from app.models.device_token import DevicePlatform, DeviceToken
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class DeviceTokenUpsert(BaseModel):
    token: str
    platform: str  # "ios" or "android"


@router.post("/device-token")
def upsert_device_token(
    payload: DeviceTokenUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    platform = payload.platform.strip().lower()
    if platform not in ("ios", "android"):
        raise HTTPException(status_code=400, detail="Platform must be 'ios' or 'android'")

    existing = (
        db.query(DeviceToken)
        .filter(DeviceToken.token == payload.token)
        .first()
    )

    if existing:
        existing.user_id = current_user.id
        existing.platform = DevicePlatform(platform)
        existing.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        dt = DeviceToken(
            user_id=current_user.id,
            token=payload.token,
            platform=DevicePlatform(platform),
        )
        db.add(dt)

    db.commit()
    return {"status": "ok"}


@router.get("/")
def list_notifications(
    unread: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread:
        query = query.filter(Notification.is_read == False)

    total = query.count()

    rows = (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()

    return {"status": "ok"}


@router.post("/read/{notification_id}")
def mark_read_post(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mark_read(notification_id=notification_id, current_user=current_user, db=db)


@router.patch("/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()

    return {"updated": count}


@router.post("/read-all")
def mark_all_read_post(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mark_all_read(current_user=current_user, db=db)
