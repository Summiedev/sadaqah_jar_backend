from datetime import datetime, timedelta, timezone
from typing import Sequence

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserDevice,
    UserMode,
    UserPreference,
    UserSession,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_user_by_google_id(db: Session, google_id: str) -> User | None:
    return db.scalar(select(User).where(User.google_id == google_id))


def link_google_account(db: Session, user: User, google_id: str) -> None:
    user.google_id = google_id
    db.add(user)
    db.commit()


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    hashed_password: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        first_name=first_name,
        last_name=last_name,
    )
    user.preferences = UserPreference()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def touch_last_active(db: Session, user: User) -> None:
    user.last_active = _utcnow()
    db.add(user)
    db.commit()


def set_mode(db: Session, user: User, mode: UserMode) -> UserPreference:
    prefs = get_or_create_preferences(db, user)
    prefs.selected_mode = mode
    db.add(prefs)
    db.commit()
    db.refresh(user)
    return user


def soft_delete(db: Session, user: User) -> None:
    user.deleted_at = _utcnow()
    db.add(user)
    db.commit()


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


def get_or_create_preferences(db: Session, user: User) -> UserPreference:
    if user.preferences is None:
        prefs = UserPreference(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        return prefs
    return user.preferences


# ---------------------------------------------------------------------------
# Sessions (refresh tokens)
# ---------------------------------------------------------------------------


REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_BYTES = 32


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_one_time_token(raw_token: str) -> str:
    """Hash reset/verification credentials before they reach persistent storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_session(db: Session, user_id: int, device_id: str | None = None) -> str:
    raw_token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    db.add(
        UserSession(
            token_hash=hash_refresh_token(raw_token),
            user_id=user_id,
            device_id=device_id,
            expires_at=_utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return raw_token


def get_valid_session(db: Session, raw_token: str) -> UserSession | None:
    token_hash = hash_refresh_token(raw_token)
    now = _utcnow()
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    if session is not None:
        session.last_used_at = now
        db.commit()
    return session


def revoke_session(db: Session, session: UserSession) -> None:
    session.revoked_at = _utcnow()
    db.add(session)
    db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> int:
    now = _utcnow()
    count = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .update({"revoked_at": now}, synchronize_session=False)
    )
    db.commit()
    return count


def list_sessions(db: Session, user_id: int) -> Sequence[UserSession]:
    return (
        db.scalars(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
        )
        .all()
    )


def get_session(db: Session, session_id: int, user_id: int) -> UserSession | None:
    return db.scalar(
        select(UserSession).where(
            UserSession.id == session_id, UserSession.user_id == user_id
        )
    )


def revoke_session_by_id(db: Session, session_id: int, user_id: int) -> bool:
    session = get_session(db, session_id, user_id)
    if session is None:
        return False
    revoke_session(db, session)
    return True


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def get_device(db: Session, user_id: int, device_id: str) -> UserDevice | None:
    return db.scalar(
        select(UserDevice).where(
            UserDevice.user_id == user_id, UserDevice.device_id == device_id
        )
    )


def get_device_by_id(db: Session, user_id: int, device_id: int) -> UserDevice | None:
    return db.scalar(
        select(UserDevice).where(
            UserDevice.id == device_id, UserDevice.user_id == user_id
        )
    )


def upsert_device(
    db: Session,
    *,
    user_id: int,
    device_id: str,
    platform: str,
    device_name: str | None,
    app_version: str | None,
    push_token: str | None,
) -> UserDevice:
    device = get_device(db, user_id, device_id)
    if device is None:
        device = UserDevice(user_id=user_id, device_id=device_id)
    device.platform = platform
    device.device_name = device_name
    device.app_version = app_version
    device.push_token = push_token
    device.last_active = _utcnow()
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def list_devices(db: Session, user_id: int) -> Sequence[UserDevice]:
    return (
        db.scalars(
            select(UserDevice)
            .where(UserDevice.user_id == user_id)
            .order_by(UserDevice.created_at.desc())
        )
        .all()
    )


def update_device(
    db: Session,
    device: UserDevice,
    *,
    device_name: str | None = None,
    push_token: str | None = None,
    app_version: str | None = None,
) -> UserDevice:
    if device_name is not None:
        device.device_name = device_name
    if push_token is not None:
        device.push_token = push_token
    if app_version is not None:
        device.app_version = app_version
    device.last_active = _utcnow()
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device: UserDevice) -> None:
    db.delete(device)
    db.commit()


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


def create_email_verification(db: Session, user_id: int) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            token_hash=hash_one_time_token(raw),
            user_id=user_id,
            expires_at=_utcnow() + timedelta(hours=24),
        )
    )
    db.commit()
    return raw


def consume_email_verification(db: Session, raw_token: str) -> User | None:
    now = _utcnow()
    vt = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_one_time_token(raw_token),
            EmailVerificationToken.expires_at > now,
        )
    )
    if vt is None:
        return None
    user = get_user_by_id(db, vt.user_id)
    if user is not None:
        user.email_verified = True
        db.add(user)
    db.delete(vt)
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def create_password_reset(db: Session, user_id: int) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            token_hash=hash_one_time_token(raw),
            user_id=user_id,
            expires_at=_utcnow() + timedelta(hours=1),
        )
    )
    db.commit()
    return raw


def consume_password_reset(
    db: Session, raw_token: str, new_hashed_password: str
) -> User | None:
    now = _utcnow()
    prt = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_one_time_token(raw_token),
            PasswordResetToken.expires_at > now,
            PasswordResetToken.used_at.is_(None),
        )
    )
    if prt is None:
        return None
    user = get_user_by_id(db, prt.user_id)
    if user is None:
        return None
    user.hashed_password = new_hashed_password
    prt.used_at = now
    db.add(user)
    db.add(prt)
    db.commit()
    return user
