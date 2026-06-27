"""In-app notification helpers."""

from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    commit: bool = True,
):
    """Create a durable in-app notification row."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)
    else:
        db.flush()
    return notification
