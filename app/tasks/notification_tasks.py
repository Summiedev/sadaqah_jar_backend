"""Event-driven notification delivery tasks.

All event-triggered notifications (goals, badges, family, invitations, etc.)
flow through these Celery tasks to get retry-with-backoff, idempotency,
preference enforcement, and async delivery decoupled from the request thread.
"""

import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.notifications.preferences import (
    is_category_enabled,
    should_delay_for_quiet_hours,
)
from app.services.notification_service import create_notification
from app.services.push_notification_service import send_push_notification

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def deliver_event_notification(
    self,
    user_id: int,
    title: str,
    message: str,
    category: str,
    notification_type: str,
    idempotency_key: str,
    action: str | None = None,
    data: dict | None = None,
) -> None:
    """Deliver an event-driven notification with retry support.

    This is the async, retry-safe delivery path for all event-triggered
    notifications: goals, badges, family activity, invitations, reading, etc.

    Idempotency: the ``idempotency_key`` prevents duplicate DB rows if the
    task is retried. The caller must also use Redis dedup to suppress
    rapid-fire duplicate events before enqueueing.

    Preferences and quiet hours are enforced here, so the caller does not
    need to check them before enqueueing.
    """
    db = SessionLocal()
    try:
        # Check in-app preference
        if not is_category_enabled(db, user_id, category, channel="in_app"):
            logger.info(
                "User %s disabled in-app for category %s, skipping",
                user_id,
                category,
            )
            return

        # Log quiet hours but do NOT drop the notification
        if should_delay_for_quiet_hours(db, user_id, category):
            logger.info(
                "User %s in quiet hours for category %s, delivering anyway (no delay queue)",
                user_id,
                category,
            )

        # Create in-app notification (idempotent)
        create_notification(
            db,
            user_id,
            title=title,
            message=message,
            category=category,
            action=action,
            idempotency_key=idempotency_key,
        )
        db.commit()

        # Send push if enabled
        if is_category_enabled(db, user_id, category, channel="push"):
            merged_data = {"notification_type": notification_type}
            if data:
                merged_data.update(data)
            send_push_notification(
                db,
                user_id=user_id,
                title=title,
                body=message,
                notification_type=notification_type,
                data=merged_data,
            )
            db.commit()

    except Exception as exc:
        db.rollback()
        logger.exception(
            "Event notification delivery failed for user %s type %s",
            user_id,
            notification_type,
        )
        try:
            self.retry(exc=exc)
        except Exception:
            # Max retries exhausted or retry failed
            logger.error(
                "Event notification delivery permanently failed for user %s key %s",
                user_id,
                idempotency_key,
            )
            raise
    finally:
        db.close()
