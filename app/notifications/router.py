"""Notifications domain router.

This module exposes the HTTP surface for:
- User notification inbox
- Notification templates (scheduling interface for background workers)
- Device registration (push-token management)

Background workers should consume the service layer directly rather than
touching these endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.notifications import service
from app.notifications.schemas import (
    NotificationTemplateCreate,
)


router = APIRouter(prefix="/notifications", tags=["notifications"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# User notification inbox
# ---------------------------------------------------------------------------


@router.get("/", response_model=Envelope)
def list_notifications(
    db: DbDep,
    current_user: CurrentUser,
    unread: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    notifications, total = service.list_notifications(
        db, current_user.id, unread=unread, limit=limit, offset=offset
    )
    return Envelope(data=notifications, meta=Meta(total=total))


@router.get("/unread-count", response_model=Envelope)
def get_unread_count(db: DbDep, current_user: CurrentUser):
    count = service.get_unread_count(db, current_user.id)
    return Envelope(data={"count": count})


@router.patch("/{notification_id}/read", response_model=Envelope)
def mark_notification_read(notification_id: int, db: DbDep, current_user: CurrentUser):
    notification = service.mark_read(db, notification_id, current_user.id)
    if notification is None:
        return Envelope(message="Notification not found")
    return Envelope(data=notification)


@router.post("/read-all", response_model=Envelope)
def mark_all_notifications_read(db: DbDep, current_user: CurrentUser):
    updated = service.mark_all_read(db, current_user.id)
    return Envelope(data={"updated": updated})


# ---------------------------------------------------------------------------
# Templates (scheduling interface)
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=Envelope)
def list_templates(
    db: DbDep,
    current_user: CurrentUser,
    category: str | None = Query(None),
    enabled: bool | None = Query(None),
):
    templates = service.list_templates(db, category=category, enabled=enabled)
    return Envelope(data=templates)


@router.post("/templates", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_template(payload: NotificationTemplateCreate, db: DbDep, current_user: CurrentUser):
    template = service.create_template(db, payload.model_dump())
    return Envelope(data=template, message="Template created")


@router.patch("/templates/{key}", response_model=Envelope)
def update_template(key: str, payload: NotificationTemplateCreate, db: DbDep, current_user: CurrentUser):
    template = service.update_template(db, key, payload.model_dump())
    if template is None:
        return Envelope(message="Template not found")
    return Envelope(data=template)


@router.delete("/templates/{key}", response_model=Envelope)
def delete_template(key: str, db: DbDep, current_user: CurrentUser):
    result = service.delete_template(db, key)
    if not result:
        return Envelope(message="Template not found")
    return Envelope(message="Template deleted")


# ---------------------------------------------------------------------------
# Device registration
# ---------------------------------------------------------------------------


@router.post("/device-token", response_model=Envelope)
def register_device_token(db: DbDep, current_user: CurrentUser, payload: dict):
    device = service.register_device(
        db,
        current_user.id,
        device_id=payload["device_id"],
        platform=payload["platform"],
        device_name=payload.get("device_name"),
        app_version=payload.get("app_version"),
        push_token=payload.get("push_token"),
    )
    return Envelope(data=device)
