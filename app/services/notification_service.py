"""In-app notification helpers."""

from sqlalchemy.orm import Session

from app.notifications.models import Notification


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    category: str | None = None,
    action: str | None = None,
    idempotency_key: str | None = None,
    commit: bool = True,
):
    """Create a durable in-app notification row.

    If an idempotency_key is supplied and a notification with that key
    already exists, the existing row is returned instead of creating a
    duplicate. This prevents retry storms and duplicate event processing
    from producing duplicate notifications.
    """
    from sqlalchemy import select as _select

    if idempotency_key:
        existing = db.scalar(
            _select(Notification).where(Notification.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return existing
    notification = Notification(
        user_id=user_id,
        category=category,
        title=title,
        message=message,
        action=action,
        idempotency_key=idempotency_key,
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)
    else:
        db.flush()
    return notification
