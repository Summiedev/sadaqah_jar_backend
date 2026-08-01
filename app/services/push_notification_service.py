"""Firebase Cloud Messaging delivery for registered user devices."""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.users.models import UserDevice

logger = logging.getLogger(__name__)


def _firebase_messaging():
    """Initialize Firebase once, only when push delivery is configured."""
    if not settings.FCM_SERVICE_ACCOUNT_PATH:
        return None
    credential_path = Path(settings.FCM_SERVICE_ACCOUNT_PATH)
    if not credential_path.is_file():
        logger.error("FCM service-account file does not exist: %s", credential_path)
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(credentials.Certificate(str(credential_path)))
        return messaging
    except Exception:
        logger.exception("Unable to initialize Firebase Admin SDK")
        return None


def validate_push_configuration() -> dict:
    """Validate push delivery configuration at startup.

    Returns a status dict describing whether push delivery is enabled and,
    if not, why. This never raises: a misconfigured or absent FCM setup must
    degrade gracefully to a no-op rather than crashing the API. The result
    is intended to be logged at startup so operators immediately see whether
    push is live.
    """
    if not settings.FCM_SERVICE_ACCOUNT_PATH:
        logger.warning(
            "Push delivery DISABLED: FCM_SERVICE_ACCOUNT_PATH is not set. "
            "In-app notifications will still be created, but no device push "
            "notifications will be sent."
        )
        return {"enabled": False, "reason": "not_configured"}

    credential_path = Path(settings.FCM_SERVICE_ACCOUNT_PATH)
    if not credential_path.is_file():
        logger.error(
            "Push delivery DISABLED: FCM service-account file not found at %s",
            credential_path,
        )
        return {"enabled": False, "reason": "credential_file_missing"}

    messaging = _firebase_messaging()
    if messaging is None:
        logger.error(
            "Push delivery DISABLED: Firebase Admin SDK failed to initialize "
            "with credentials at %s",
            credential_path,
        )
        return {"enabled": False, "reason": "init_failed"}

    logger.info("Push delivery ENABLED via FCM (%s)", credential_path)
    return {"enabled": True, "reason": None}



def send_push_notification(
    db: Session, *, user_id: int, title: str, body: str, notification_type: str = 'general', data: dict[str, str] | None = None
) -> int:
    """Send to every active device token registered for one user."""
    messaging = _firebase_messaging()
    if messaging is None:
        return 0
    merged_data = {'notification_type': notification_type}
    if data:
        merged_data.update(data)
    devices = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == user_id, UserDevice.push_token.is_not(None))
        .all()
    )
    delivered = 0
    for device in devices:
        try:
            messaging.send(
                messaging.Message(
                    token=device.push_token,
                    notification=messaging.Notification(title=title, body=body),
                    data=merged_data,
                )
            )
            delivered += 1
        except Exception as exc:
            code = getattr(exc, "code", "")
            if code in {"registration-token-not-registered", "invalid-registration-token"}:
                device.push_token = None
            logger.warning("FCM delivery failed for device %s: %s", device.id, exc)
    db.flush()
    return delivered
