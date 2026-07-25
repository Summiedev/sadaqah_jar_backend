"""Notifications domain repository layer."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.notifications.models import (
    Notification,
    NotificationTemplate,
)
from app.users.models import UserDevice


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def list_notifications(
    db: Session,
    user_id: int,
    unread: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Notification], int]:
    query = db.query(Notification).filter(Notification.user_id == user_id)

    if unread:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()

    rows = (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def get_notification(db: Session, notification_id: int, user_id: int) -> Notification | None:
    return db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    category: str | None = None,
    action: str | None = None,
    commit: bool = True,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        category=category,
        title=title,
        message=message,
        action=action,
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)
    else:
        db.flush()
    return notification


def mark_notification_read(db: Session, notification_id: int, user_id: int) -> Notification | None:
    notification = get_notification(db, notification_id, user_id)
    if notification is not None and not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id: int) -> int:
    result = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return result


def get_unread_count(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ) or 0


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def list_templates(
    db: Session, category: str | None = None, enabled: bool | None = None
) -> Sequence[NotificationTemplate]:
    query = db.query(NotificationTemplate)
    if category is not None:
        query = query.filter(NotificationTemplate.category == category)
    if enabled is not None:
        query = query.filter(NotificationTemplate.enabled == enabled)
    return query.order_by(NotificationTemplate.category, NotificationTemplate.key).all()


def get_template_by_key(db: Session, key: str) -> NotificationTemplate | None:
    return db.scalar(
        select(NotificationTemplate).where(NotificationTemplate.key == key)
    )


def create_template(db: Session, payload: dict) -> NotificationTemplate:
    template = NotificationTemplate(
        key=payload["key"],
        title_template=payload["title_template"],
        message_template=payload["message_template"],
        category=payload["category"],
        strategy=payload["strategy"],
        strategy_config=payload.get("strategy_config"),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(db: Session, key: str, payload: dict) -> NotificationTemplate | None:
    template = get_template_by_key(db, key)
    if template is None:
        return None

    for field in ("title_template", "message_template", "category", "strategy", "strategy_config", "enabled"):
        if field in payload:
            setattr(template, field, payload[field])

    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, key: str) -> bool:
    template = get_template_by_key(db, key)
    if template is None:
        return False
    db.delete(template)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def get_device(db: Session, user_id: int, device_id: str) -> UserDevice | None:
    return db.scalar(
        select(UserDevice).where(
            UserDevice.user_id == user_id,
            UserDevice.device_id == device_id,
        )
    )


def list_devices(db: Session, user_id: int) -> Sequence[UserDevice]:
    return db.scalars(
        select(UserDevice).where(UserDevice.user_id == user_id)
    ).all()


def upsert_device(
    db: Session,
    user_id: int,
    device_id: str,
    platform: str,
    device_name: str | None = None,
    app_version: str | None = None,
    push_token: str | None = None,
    commit: bool = True,
) -> UserDevice:
    device = get_device(db, user_id, device_id)
    if device is None:
        device = UserDevice(
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            device_name=device_name,
            app_version=app_version,
            push_token=push_token,
        )
        db.add(device)
    else:
        device.platform = platform
        device.device_name = device_name
        device.app_version = app_version
        device.push_token = push_token
        device.last_active = _utcnow()

    if commit:
        db.commit()
        db.refresh(device)
    else:
        db.flush()
    return device


def update_device(
    db: Session,
    user_id: int,
    device_id: str,
    device_name: str | None = None,
    push_token: str | None = None,
    app_version: str | None = None,
) -> UserDevice | None:
    device = get_device(db, user_id, device_id)
    if device is None:
        return None

    if device_name is not None:
        device.device_name = device_name
    if push_token is not None:
        device.push_token = push_token
    if app_version is not None:
        device.app_version = app_version

    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, user_id: int, device_id: str) -> bool:
    device = get_device(db, user_id, device_id)
    if device is None:
        return False
    db.delete(device)
    db.commit()
    return True
