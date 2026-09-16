"""Admin CRUD for in-app announcements."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.deps import get_db
from app.models.broadcast import Broadcast, BroadcastReceipt
from app.schemas.broadcast import BroadcastCreate, BroadcastUpdate

router = APIRouter(prefix="/admin/broadcasts", tags=["Admin Broadcasts"])


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _serialize(item: Broadcast, *, views: int = 0, dismissals: int = 0, clicks: int = 0) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "body": item.body,
        "image_url": item.image_url,
        "cta_label": item.cta_label,
        "cta_link": item.cta_link,
        "starts_at": item.starts_at,
        "ends_at": item.ends_at,
        "audience": item.audience,
        "display_mode": item.display_mode,
        "is_active": item.is_active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "analytics": {"views": views, "dismissals": dismissals, "clicks": clicks},
    }


def _counts(db: Session, broadcast_id: int) -> tuple[int, int, int]:
    row = db.execute(
        select(
            func.count(BroadcastReceipt.viewed_at),
            func.count(BroadcastReceipt.dismissed_at),
            func.count(BroadcastReceipt.clicked_at),
        ).where(BroadcastReceipt.broadcast_id == broadcast_id)
    ).one()
    return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)


def _dump(db: Session, item: Broadcast) -> dict:
    views, dismissals, clicks = _counts(db, item.id)
    return _serialize(
        item,
        views=views,
        dismissals=dismissals,
        clicks=clicks,
    )


@router.get("/")
def list_broadcasts(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
    include_inactive: bool = Query(True),
):
    query = select(Broadcast).order_by(Broadcast.created_at.desc(), Broadcast.id.desc())
    if not include_inactive:
        query = query.where(Broadcast.is_active.is_(True))
    return {"data": [_dump(db, item) for item in db.scalars(query).all()]}


@router.post("/", status_code=201)
def create_broadcast(payload: BroadcastCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if payload.ends_at and payload.starts_at and payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="End date must be after start date")
    item = Broadcast(
        **payload.model_dump(exclude={"starts_at", "ends_at"}),
        starts_at=_utc(payload.starts_at),
        ends_at=_utc(payload.ends_at) if payload.ends_at else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _dump(db, item)


@router.patch("/{broadcast_id}")
def update_broadcast(
    broadcast_id: int,
    payload: BroadcastUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    item = db.get(Broadcast, broadcast_id)
    if not item:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        if key in {"starts_at", "ends_at"}:
            value = _utc(value) if value else None
        setattr(item, key, value)
    if item.ends_at and item.ends_at <= item.starts_at:
        raise HTTPException(status_code=422, detail="End date must be after start date")
    db.commit()
    db.refresh(item)
    return _dump(db, item)


@router.delete("/{broadcast_id}")
def delete_broadcast(broadcast_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    item = db.get(Broadcast, broadcast_id)
    if not item:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    item.is_active = False
    db.commit()
    return {"message": "Broadcast archived"}
