"""Notifications domain router.

This module exposes the HTTP surface for:
- User notification inbox
- Notification templates (scheduling interface for background workers)
- Device registration (push-token management)

Background workers should consume the service layer directly rather than
touching these endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.users.permissions import require_admin
from app.notifications import service

from app.notifications.preference_schemas import (
    NotificationPreferencesUpdate,
)
from app.notifications.preferences import get_category_state
from app.notifications.schemas import (
    DeviceTokenRequest,
    NotificationTemplateCreate,
)
from app.users.models import UserPreference
import json


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
        raise HTTPException(status_code=404, detail="Notification not found")
    return Envelope(data=notification)


@router.delete("/{notification_id}", response_model=Envelope)
def delete_notification(notification_id: int, db: DbDep, current_user: CurrentUser):
    service.delete_notification(db, notification_id, current_user.id)
    return Envelope(message="Notification deleted")


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
    _admin: Annotated[User, Depends(require_admin)],
    category: str | None = Query(None),
    enabled: bool | None = Query(None),
):
    templates = service.list_templates(db, category=category, enabled=enabled)
    return Envelope(data=templates)


@router.post("/templates", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: NotificationTemplateCreate,
    db: DbDep,
    _admin: Annotated[User, Depends(require_admin)],
):
    template = service.create_template(db, payload.model_dump())
    return Envelope(data=template, message="Template created")


@router.patch("/templates/{key}", response_model=Envelope)
def update_template(
    key: str,
    payload: NotificationTemplateCreate,
    db: DbDep,
    _admin: Annotated[User, Depends(require_admin)],
):
    template = service.update_template(db, key, payload.model_dump())
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return Envelope(data=template)


@router.delete("/templates/{key}", response_model=Envelope)
def delete_template(
    key: str,
    db: DbDep,
    _admin: Annotated[User, Depends(require_admin)],
):
    result = service.delete_template(db, key)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return Envelope(message="Template deleted")


# ---------------------------------------------------------------------------
# Notification preferences
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {
    "prayer_fardh": "Daily Prayers",
    "prayer_nafl": "Nafl Prayers",
    "adhkar_morning": "Morning Adhkar",
    "adhkar_evening": "Evening Adhkar",
    "time_based": "Time-Based Reminders",
    "quran": "Quran Verses",
    "hadith": "Hadith",
    "reflection": "Reflection Prompts",
    "hereafter": "Hereafter & Accountability",
    "good_deeds": "Good Deeds & Sunnah",
    "quotes": "Motivational Quotes",
    "family": "Family",
    "journey": "Journey",
    "prayer": "Prayer",
    "adhkar": "Adhkar",
    "reading": "Reading",
    "charity": "Charity",
    "islamic_occasions": "Islamic Occasions",
    "announcements": "Announcements",
    "security": "Security",
    "system": "System",
}


@router.get("/preferences", response_model=Envelope)
def get_notification_preferences(db: DbDep, current_user: CurrentUser):
    state = get_category_state(db, current_user.id)
    state["category_labels"] = CATEGORY_LABELS
    return Envelope(data=state)


@router.put("/preferences", response_model=Envelope)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    pref = db.get(UserPreference, current_user.id)
    if pref is None:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
    try:
        data = json.loads(pref.notification_preferences or "{}")
    except (json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    if payload.all_enabled is not None:
        data["all_enabled"] = payload.all_enabled
    if payload.frequency is not None:
        data["frequency"] = payload.frequency
    if payload.categories is not None:
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        categories.update(payload.categories)
        data["categories"] = categories
    if payload.quiet_hours is not None:
        data["quiet_hours"] = payload.quiet_hours.model_dump()
    pref.notification_preferences = json.dumps(data)
    db.add(pref)
    db.commit()
    state = get_category_state(db, current_user.id)
    state["category_labels"] = CATEGORY_LABELS
    return Envelope(data=state)


# ---------------------------------------------------------------------------
# Device registration
# ---------------------------------------------------------------------------


@router.post("/device-token", response_model=Envelope)
def register_device_token(
    db: DbDep, current_user: CurrentUser, payload: DeviceTokenRequest
):
    device = service.register_device(
        db,
        current_user.id,
        device_id=payload.device_id,
        platform=payload.platform,
        device_name=payload.device_name,
        app_version=payload.app_version,
        push_token=payload.push_token,
    )
    return Envelope(data=device)
