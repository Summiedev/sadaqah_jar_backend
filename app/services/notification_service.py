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
    commit: bool = True,
):
    """Create a durable in-app notification row."""
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
