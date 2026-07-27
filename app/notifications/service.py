"""Notifications domain service layer."""

import json

from sqlalchemy.orm import Session

from app.notifications import repository as repo
from app.notifications.exceptions import (
    DeviceNotFoundException,
    NotificationNotFoundException,
    TemplateNotFoundException,
)
from app.notifications.schemas import (
    NotificationResponse,
    NotificationTemplateResponse,
)


def _strategy_config(value: str | dict | None) -> dict | None:
    if isinstance(value, dict) or value is None:
        return value
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


# ---------------------------------------------------------------------------
# Public interface for background workers
# ---------------------------------------------------------------------------


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    category: str | None = None,
    action: str | None = None,
) -> NotificationResponse:
    notification = repo.create_notification(
        db, user_id, title=title, message=message, category=category, action=action
    )
    return NotificationResponse(
        id=notification.id,
        category=notification.category,
        title=notification.title,
        message=notification.message,
        action=notification.action,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def list_notifications(
    db: Session,
    user_id: int,
    unread: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[NotificationResponse], int]:
    rows, total = repo.list_notifications(
        db, user_id, unread=unread, limit=limit, offset=offset
    )
    return (
        [
            NotificationResponse(
                id=n.id,
                category=n.category,
                title=n.title,
                message=n.message,
                action=n.action,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in rows
        ],
        total,
    )


def get_notification(db: Session, notification_id: int, user_id: int) -> NotificationResponse:
    notification = repo.get_notification(db, notification_id, user_id)
    if not notification:
        raise NotificationNotFoundException("Notification not found")
    return NotificationResponse(
        id=notification.id,
        category=notification.category,
        title=notification.title,
        message=notification.message,
        action=notification.action,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


def mark_read(db: Session, notification_id: int, user_id: int) -> NotificationResponse | None:
    notification = repo.mark_notification_read(db, notification_id, user_id)
    if notification is None:
        raise NotificationNotFoundException("Notification not found")
    return NotificationResponse(
        id=notification.id,
        category=notification.category,
        title=notification.title,
        message=notification.message,
        action=notification.action,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


def mark_all_read(db: Session, user_id: int) -> int:
    return repo.mark_all_notifications_read(db, user_id)


def delete_notification(db: Session, notification_id: int, user_id: int) -> None:
    repo.delete_notification(db, notification_id, user_id)


def get_unread_count(db: Session, user_id: int) -> int:
    return repo.get_unread_count(db, user_id)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def list_templates(
    db: Session, category: str | None = None, enabled: bool | None = None
) -> list[NotificationTemplateResponse]:
    templates = repo.list_templates(db, category=category, enabled=enabled)
    return [
        NotificationTemplateResponse(
            id=t.id,
            key=t.key,
            title_template=t.title_template,
            message_template=t.message_template,
            category=t.category,
            strategy=t.strategy,
            strategy_config=_strategy_config(t.strategy_config),
            enabled=t.enabled,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


def get_template(db: Session, key: str) -> NotificationTemplateResponse:
    template = repo.get_template_by_key(db, key)
    if not template:
        raise TemplateNotFoundException("Template not found")
    return NotificationTemplateResponse(
        id=template.id,
        key=template.key,
        title_template=template.title_template,
        message_template=template.message_template,
        category=template.category,
        strategy=template.strategy,
        strategy_config=_strategy_config(template.strategy_config),
        enabled=template.enabled,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def create_template(db: Session, payload: dict) -> NotificationTemplateResponse:
    template = repo.create_template(db, payload)
    return NotificationTemplateResponse(
        id=template.id,
        key=template.key,
        title_template=template.title_template,
        message_template=template.message_template,
        category=template.category,
        strategy=template.strategy,
        strategy_config=_strategy_config(template.strategy_config),
        enabled=template.enabled,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def update_template(db: Session, key: str, payload: dict) -> NotificationTemplateResponse:
    template = repo.update_template(db, key, payload)
    if not template:
        raise TemplateNotFoundException("Template not found")
    return NotificationTemplateResponse(
        id=template.id,
        key=template.key,
        title_template=template.title_template,
        message_template=template.message_template,
        category=template.category,
        strategy=template.strategy,
        strategy_config=_strategy_config(template.strategy_config),
        enabled=template.enabled,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def delete_template(db: Session, key: str) -> bool:
    return repo.delete_template(db, key)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def register_device(
    db: Session,
    user_id: int,
    device_id: str,
    platform: str,
    device_name: str | None = None,
    app_version: str | None = None,
    push_token: str | None = None,
) -> dict:
    device = repo.upsert_device(
        db,
        user_id,
        device_id,
        platform,
        device_name=device_name,
        app_version=app_version,
        push_token=push_token,
    )
    return {"status": "ok", "device_id": device.device_id}


def list_devices(db: Session, user_id: int) -> list[dict]:
    devices = repo.list_devices(db, user_id)
    return [
        {
            "id": d.id,
            "device_id": d.device_id,
            "platform": d.platform,
            "device_name": d.device_name,
            "app_version": d.app_version,
            "has_push_token": bool(d.push_token),
            "last_active": d.last_active.isoformat() if d.last_active else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in devices
    ]


def update_device(
    db: Session,
    user_id: int,
    device_id: str,
    device_name: str | None = None,
    push_token: str | None = None,
    app_version: str | None = None,
) -> dict:
    device = repo.update_device(
        db,
        user_id,
        device_id,
        device_name=device_name,
        push_token=push_token,
        app_version=app_version,
    )
    if not device:
        raise DeviceNotFoundException("Device not found")
    return {"status": "ok"}


def delete_device(db: Session, user_id: int, device_id: str) -> None:
    result = repo.delete_device(db, user_id, device_id)
    if not result:
        raise DeviceNotFoundException("Device not found")
