import json

import httpx
import secrets
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessRuleException
from app.core.security import create_access_token, hash_password, verify_password
from app.services.email_service import send_verification_email
from app.users import repository as repo
from app.users.exceptions import (
    EmailTakenException,
    ForbiddenException,
    GoogleOAuthException,
    InvalidCredentialsException,
    InvalidTokenException,
    ResourceNotFoundException,
    UsernameTakenException,
)
from app.users.models import User, UserPreference, UserSession
from app.users.repository import (
    create_session,
    get_valid_session,
    link_google_account,
    revoke_session,
    revoke_session_by_id,
    revoke_all_sessions,
    list_sessions,
    get_user_by_google_id,
)
from app.users.schemas import (
    ChangePasswordRequest,
    DeviceResponse,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    PushTokenRequest,
    ResendVerificationRequest,
    SessionResponse,
    UserModeUpdate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserRegister,
)
from app.users.validators import validate_email, validate_username


def _issue_tokens(db: Session, user: User, device_id: str | None = None) -> dict:
    access = create_access_token({"sub": str(user.id)})
    refresh = create_session(db, user.id, device_id=device_id)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Registration / Login / Logout / Refresh
# ---------------------------------------------------------------------------


def register(db: Session, payload: UserRegister, device_id: str | None = None) -> dict:
    email = validate_email(payload.email)
    username = validate_username(payload.username)
    if email is None or username is None:
        raise ForbiddenException("Email and username are required")

    if repo.get_user_by_email(db, email):
        raise EmailTakenException()
    if repo.get_user_by_username(db, username):
        raise UsernameTakenException()

    user = repo.create_user(
        db,
        username=username,
        email=email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name if hasattr(payload, "first_name") else None,
        last_name=payload.last_name if hasattr(payload, "last_name") else None,
    )
    return _issue_tokens(db, user, device_id=device_id)


def login(db: Session, email: str, password: str, device_id: str | None = None) -> dict:
    user = repo.get_user_by_email(db, validate_email(email) or "")
    if user is None or user.deleted_at is not None or not verify_password(
        password, user.hashed_password
    ):
        raise InvalidCredentialsException()
    repo.touch_last_active(db, user)
    return _issue_tokens(db, user, device_id=device_id)


def refresh(db: Session, raw_token: str, device_id: str | None = None) -> dict:
    session = get_valid_session(db, raw_token)
    if session is None:
        raise InvalidTokenException()
    revoke_session(db, session)
    user = repo.get_user_by_id(db, session.user_id)
    if user is None or user.deleted_at is not None:
        raise InvalidTokenException()
    return _issue_tokens(db, user, device_id=device_id)


def logout(db: Session, raw_token: str) -> None:
    session = get_valid_session(db, raw_token)
    if session is not None:
        revoke_session(db, session)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def _profile_response(db: Session, user: User) -> UserProfileResponse:
    prefs = repo.get_or_create_preferences(db, user)
    notifications = _prefs_to_dict(prefs)["notification_preferences"]
    return UserProfileResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified,
        role=user.role,
        mode=prefs.selected_mode,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_data=user.avatar_data,
        timezone=prefs.timezone,
        locale=prefs.language,
        evidence_mode=bool(notifications.get("evidence_mode", False)),
        friday_reminder=bool(notifications.get("friday_reminder", False)),
        last_active=user.last_active.isoformat() if user.last_active else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def get_profile(db: Session, user: User) -> UserProfileResponse:
    return _profile_response(db, user)


def update_profile(db: Session, user: User, payload: UserProfileUpdate) -> UserProfileResponse:
    if payload.username is not None:
        username = validate_username(payload.username)
        if username is None:
            raise ForbiddenException("Username cannot be empty")
        if username != user.username:
            if repo.get_user_by_username(db, username):
                raise UsernameTakenException()
            user.username = username

    if payload.email is not None:
        email = validate_email(payload.email)
        if email is None:
            raise EmailTakenException()
        if email != user.email:
            if repo.get_user_by_email(db, email):
                raise EmailTakenException()
            user.email = email
            user.email_verified = False

    if payload.first_name is not None:
        user.first_name = payload.first_name or None
    if payload.last_name is not None:
        user.last_name = payload.last_name or None
    if payload.avatar_data is not None:
        user.avatar_data = payload.avatar_data.strip() or None
    if payload.timezone is not None:
        prefs = repo.get_or_create_preferences(db, user)
        prefs.timezone = payload.timezone.strip() or None
    if payload.locale is not None:
        prefs = repo.get_or_create_preferences(db, user)
        prefs.language = payload.locale.strip() or "en"

    db.add(user)
    db.commit()
    db.refresh(user)
    return _profile_response(db, user)


# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------


def update_mode(db: Session, user: User, payload: UserModeUpdate) -> UserProfileResponse:
    repo.set_mode(db, user, payload.mode)
    return _profile_response(db, user)


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


def _prefs_to_dict(prefs: UserPreference) -> dict:
    def load(field: str) -> dict:
        try:
            return json.loads(field) if field else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    return {
        "theme": prefs.theme,
        "language": prefs.language,
        "timezone": prefs.timezone,
        "selected_mode": prefs.selected_mode,
        "notification_preferences": load(prefs.notification_preferences),
        "reminder_preferences": load(prefs.reminder_preferences),
        "accessibility_preferences": load(prefs.accessibility_preferences),
        "privacy_preferences": load(prefs.privacy_preferences),
    }


def _dump(value: dict | None) -> str:
    return json.dumps(value if value is not None else {})


def get_preferences(db: Session, user: User) -> UserPreferencesResponse:
    prefs = repo.get_or_create_preferences(db, user)
    data = _prefs_to_dict(prefs)
    return UserPreferencesResponse(**data)


def update_preferences(
    db: Session, user: User, payload: UserPreferencesUpdate
) -> UserPreferencesResponse:
    prefs = repo.get_or_create_preferences(db, user)
    if payload.theme is not None:
        prefs.theme = payload.theme
    if payload.language is not None:
        prefs.language = payload.language
    if payload.timezone is not None:
        prefs.timezone = payload.timezone.strip() or None
    if payload.notification_preferences is not None:
        prefs.notification_preferences = _dump(payload.notification_preferences)
    # Active Flutter clients send these flat fields; retain them inside the
    # feature-owned notification preference document.
    existing_notifications = _prefs_to_dict(prefs)["notification_preferences"]
    if getattr(payload, "friday_reminder", None) is not None:
        existing_notifications["friday_reminder"] = payload.friday_reminder
    if getattr(payload, "evidence_mode", None) is not None:
        existing_notifications["evidence_mode"] = payload.evidence_mode
    if getattr(payload, "friday_reminder", None) is not None or getattr(payload, "evidence_mode", None) is not None:
        prefs.notification_preferences = _dump(existing_notifications)
    if payload.reminder_preferences is not None:
        prefs.reminder_preferences = _dump(payload.reminder_preferences)
    if payload.accessibility_preferences is not None:
        prefs.accessibility_preferences = _dump(payload.accessibility_preferences)
    if payload.privacy_preferences is not None:
        prefs.privacy_preferences = _dump(payload.privacy_preferences)
    db.add(prefs)
    db.commit()
    return get_preferences(db, user)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def _session_response(session: UserSession, current_token_hash: str | None) -> dict:
    return SessionResponse(
        id=session.id,
        device_id=session.device_id,
        created_at=session.created_at.isoformat() if session.created_at else None,
        last_used_at=session.last_used_at.isoformat() if session.last_used_at else None,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        is_current=bool(
            current_token_hash and session.token_hash == current_token_hash
        ),
    ).model_dump()


def list_user_sessions(db: Session, user: User, current_token_hash: str | None) -> list[dict]:
    sessions = list_sessions(db, user.id)
    return [_session_response(s, current_token_hash) for s in sessions]


def logout_session(db: Session, user: User, session_id: int) -> None:
    if not revoke_session_by_id(db, session_id, user.id):
        raise ResourceNotFoundException("Session not found")


def logout_everywhere(db: Session, user: User) -> int:
    return revoke_all_sessions(db, user.id)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def register_push_token(db: Session, user: User, payload: PushTokenRequest) -> dict:
    repo.upsert_device(
        db,
        user_id=user.id,
        device_id=payload.device_id,
        platform=payload.platform,
        device_name=payload.device_name,
        app_version=payload.app_version,
        push_token=payload.push_token,
    )
    return {"status": "ok"}


def list_user_devices(db: Session, user: User) -> list[dict]:
    devices = repo.list_devices(db, user.id)
    return [
        DeviceResponse(
            id=d.id,
            device_id=d.device_id,
            platform=d.platform,
            device_name=d.device_name,
            app_version=d.app_version,
            has_push_token=bool(d.push_token),
            last_active=d.last_active.isoformat() if d.last_active else None,
            created_at=d.created_at.isoformat() if d.created_at else None,
        ).model_dump()
        for d in devices
    ]


def update_user_device(
    db: Session,
    user: User,
    device_id: int,
    device_name: str | None,
    push_token: str | None,
    app_version: str | None,
) -> dict:
    device = repo.get_device_by_id(db, user.id, device_id)
    if device is None:
        raise ResourceNotFoundException("Device not found")
    repo.update_device(db, device, device_name=device_name, push_token=push_token, app_version=app_version)
    return {"status": "ok"}


def delete_user_device(db: Session, user: User, device_id: int) -> None:
    device = repo.get_device_by_id(db, user.id, device_id)
    if device is None:
        raise ResourceNotFoundException("Device not found")
    repo.delete_device(db, device)


# ---------------------------------------------------------------------------
# Email verification / password recovery
# ---------------------------------------------------------------------------


def forgot_password(db: Session, email: str) -> ForgotPasswordResponse:
    user = repo.get_user_by_email(db, validate_email(email) or "")
    if user and user.deleted_at is None:
        repo.create_password_reset(db, user.id)
    return ForgotPasswordResponse()


def reset_password(db: Session, token: str, new_password: str) -> None:
    user = repo.consume_password_reset(db, token, hash_password(new_password))
    if user is None:
        raise InvalidTokenException()
    # A password reset invalidates every existing refresh session.
    repo.revoke_all_sessions(db, user.id)


def verify_email(db: Session, token: str) -> None:
    if repo.consume_email_verification(db, token) is None:
        raise InvalidTokenException()


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise ForbiddenException("Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    repo.revoke_all_sessions(db, user.id)


# ---------------------------------------------------------------------------
# Resend verification
# ---------------------------------------------------------------------------


def resend_verification(db: Session, payload: ResendVerificationRequest) -> dict:
    email = validate_email(payload.email) or ""
    user = repo.get_user_by_email(db, email)
    if user is None or user.deleted_at is not None:
        return {"message": "If an account with that email exists and is not verified, a new verification link has been sent."}
    if user.email_verified:
        raise BusinessRuleException("Email is already verified")
    raw_token = repo.create_email_verification(db, user.id)
    send_verification_email(user.email, raw_token, user.first_name or user.username)
    return {"message": "If an account with that email exists and is not verified, a new verification link has been sent."}


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


def _derive_username(email: str) -> str:
    local = email.split("@")[0]
    safe = "".join(c for c in local if c.isalnum() or c in "_-")
    return safe[:50].strip() or "user"


def google_auth(db: Session, payload: GoogleAuthRequest) -> dict:
    id_token = payload.id_token.strip()
    if not id_token:
        raise InvalidTokenException("Missing Google ID token")
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise InvalidTokenException("Invalid Google ID token") from exc

    google_id = data.get("sub")
    email = data.get("email")
    email_verified = data.get("email_verified") == "true"

    if not google_id or not email or not email_verified:
        raise GoogleOAuthException("Google token missing required fields")

    user = get_user_by_google_id(db, google_id)
    if user is None:
        user = repo.get_user_by_email(db, email)
        if user is None:
            base_username = _derive_username(email)
            username = base_username
            counter = 1
            while repo.get_user_by_username(db, username) is not None:
                username = f"{base_username}{counter}"
                counter += 1
            random_password = secrets.token_urlsafe(32)
            user = repo.create_user(
                db,
                username=username,
                email=email,
                hashed_password=hash_password(random_password),
                first_name=data.get("given_name"),
                last_name=data.get("family_name"),
            )
        link_google_account(db, user, google_id)
    return _issue_tokens(db, user)


def get_google_auth_url() -> dict:
    import urllib.parse

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": url}
