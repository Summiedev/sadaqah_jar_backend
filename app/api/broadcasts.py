"""Authenticated user endpoints for active in-app announcements."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.envelope import Envelope
from app.db.deps import get_db
from app.models.broadcast import Broadcast, BroadcastReceipt
from app.users.dependencies import get_current_user
from app.users.models import Role, User

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])
DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize(item: Broadcast, receipt: BroadcastReceipt | None = None) -> dict:
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
        "viewed": receipt is not None and receipt.viewed_at is not None,
    }


def _audience_matches(item: Broadcast, user: User) -> bool:
    return item.audience == "all" or (
        item.audience == "admins" and user.role == Role.ADMIN
    ) or (item.audience == "verified" and user.email_verified)


def _receipt(db: Session, user_id: int, broadcast_id: int) -> BroadcastReceipt | None:
    return db.scalar(
        select(BroadcastReceipt).where(
            BroadcastReceipt.user_id == user_id,
            BroadcastReceipt.broadcast_id == broadcast_id,
        )
    )


@router.get("/active", response_model=Envelope)
def active_broadcasts(db: DbDep, current_user: CurrentUser):
    now = _now()
    rows = db.scalars(
        select(Broadcast)
        .where(
            Broadcast.is_active.is_(True),
            Broadcast.starts_at <= now,
            (Broadcast.ends_at.is_(None) | (Broadcast.ends_at > now)),
        )
        .order_by(Broadcast.starts_at.desc(), Broadcast.id.desc())
    ).all()
    result = []
    for item in rows:
        if not _audience_matches(item, current_user):
            continue
        receipt = _receipt(db, current_user.id, item.id)
        if item.display_mode == "once" and receipt and receipt.viewed_at:
            continue
        if item.display_mode == "until_dismissed" and receipt and receipt.dismissed_at:
            continue
        result.append(_serialize(item, receipt))
    return Envelope(data=result)


def _record(db: Session, user: User, broadcast_id: int, field: str):
    item = db.get(Broadcast, broadcast_id)
    now = _now()
    if (
        not item
        or not item.is_active
        or item.starts_at > now
        or (item.ends_at is not None and item.ends_at <= now)
        or not _audience_matches(item, user)
    ):
        raise HTTPException(status_code=404, detail="Broadcast not found")
    receipt = _receipt(db, user.id, broadcast_id)
    if receipt is None:
        try:
            # The unique key makes receipts idempotent. The savepoint handles
            # two devices recording the first event at the same time without
            # turning a harmless race into a 500 response.
            with db.begin_nested():
                receipt = BroadcastReceipt(broadcast_id=broadcast_id, user_id=user.id)
                db.add(receipt)
                db.flush()
        except IntegrityError:
            receipt = _receipt(db, user.id, broadcast_id)
    if receipt is None:
        raise HTTPException(status_code=409, detail="Could not record broadcast event")
    setattr(receipt, field, now)
    db.commit()
    return {"broadcast_id": broadcast_id, "recorded": field}


@router.post("/{broadcast_id}/view", response_model=Envelope)
def record_view(broadcast_id: int, db: DbDep, current_user: CurrentUser):
    return Envelope(data=_record(db, current_user, broadcast_id, "viewed_at"))


@router.post("/{broadcast_id}/dismiss", response_model=Envelope)
def record_dismissal(broadcast_id: int, db: DbDep, current_user: CurrentUser):
    return Envelope(data=_record(db, current_user, broadcast_id, "dismissed_at"))


@router.post("/{broadcast_id}/click", response_model=Envelope)
def record_click(broadcast_id: int, db: DbDep, current_user: CurrentUser):
    return Envelope(data=_record(db, current_user, broadcast_id, "clicked_at"))
