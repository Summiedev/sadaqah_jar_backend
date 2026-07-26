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


def send_push_notification(
    db: Session, *, user_id: int, title: str, body: str, data: dict[str, str] | None = None
) -> int:
    """Send to every active device token registered for one user."""
    messaging = _firebase_messaging()
    if messaging is None:
        return 0
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
                    data=data or {},
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
