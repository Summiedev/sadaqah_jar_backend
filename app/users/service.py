import json

import httpx
import secrets
from sqlalchemy.orm import Session

from app.core.audit import audit_logger
from app.core.config import settings
from app.core.exceptions import BusinessRuleException, ResourceNotFoundException
from app.core.security import create_access_token, hash_password, verify_password
from app.services.email_service import send_verification_email, send_password_reset_email, send_email
from app.emails.templates import (
    verification_email_html,
    password_reset_email_html,
    email_change_request_html,
    email_change_notification_html,
    email_change_confirmed_html,
)
from app.users import repository as repo
from app.users.exceptions import (
    EmailTakenException,
    ForbiddenException,
    GoogleOAuthException,
    InvalidCredentialsException,
    InvalidTokenException,
    UsernameTakenException,
)
from app.users.models import PendingEmailChange, Role
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
    get_pending_email_change,
    get_pending_email_change_by_token,
    confirm_pending_email_change,
    cancel_pending_email_change,
    create_pending_email_change,
)
from app.users.schemas import (
    ChangePasswordRequest,
    ConfirmEmailChangeRequest,
    ConfirmEmailChangeResponse,
    DeviceResponse,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    PendingEmailChangeResponse,
    PushTokenRequest,
    RequestEmailChangeRequest,
    RequestEmailChangeResponse,
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

    requested_role = None
    if payload.role in {Role.ADMIN.value, "ADMIN"}:
        existing_count = db.query(User).count()
        if existing_count == 0:
            requested_role = Role.ADMIN

    user = repo.create_user(
        db,
        username=username,
        email=email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=requested_role,
    )
    raw_token = repo.create_email_verification(db, user.id)
    send_verification_email(user.email, raw_token, user.first_name or user.username)
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
        latitude=user.latitude,
        longitude=user.longitude,
        locale=prefs.language,
        evidence_mode=bool(notifications.get("evidence_mode", False)),
        friday_reminder=bool(notifications.get("friday_reminder", False)),
        general_notifications=bool(notifications.get("general_notifications", False)),
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
        raise ForbiddenException(
            "Email changes are not allowed through this endpoint. "
            "Use POST /users/me/email/change-request to start an email change."
        )

    if payload.first_name is not None:
        user.first_name = payload.first_name or None
    if payload.last_name is not None:
        user.last_name = payload.last_name or None
    if payload.avatar_data is not None:
        user.avatar_data = payload.avatar_data.strip() or None
    if payload.timezone is not None:
        prefs = repo.get_or_create_preferences(db, user)
        prefs.timezone = payload.timezone.strip() or None
    if payload.latitude is not None:
        user.latitude = payload.latitude
        user.longitude = payload.longitude
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
    if getattr(payload, "general_notifications", None) is not None:
        existing_notifications["general_notifications"] = payload.general_notifications
    if (
        getattr(payload, "friday_reminder", None) is not None
        or getattr(payload, "evidence_mode", None) is not None
        or getattr(payload, "general_notifications", None) is not None
    ):
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
    # Persist device-level push token info
    repo.upsert_device(
        db,
        user_id=user.id,
        device_id=payload.device_id,
        platform=payload.platform,
        device_name=payload.device_name,
        app_version=payload.app_version,
        push_token=payload.push_token,
    )

    # Persist optional timezone and coordinates on the user's profile/preferences.
    # The mobile client provides these so the server can schedule timezone-aware
    # deliveries (prayer reminders, quiet-hours, etc.). We store timezone on the
    # user's preferences and coordinates on the user record.
    updated = False
    if getattr(payload, "timezone", None) is not None:
        prefs = repo.get_or_create_preferences(db, user)
        prefs.timezone = payload.timezone.strip() or None
        db.add(prefs)
        updated = True
    if getattr(payload, "latitude", None) is not None:
        user.latitude = payload.latitude
        user.longitude = payload.longitude
        db.add(user)
        updated = True

    if updated:
        db.commit()

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
        raw_token = repo.create_password_reset(db, user.id)
        send_password_reset_email(user.email, raw_token)
    return ForgotPasswordResponse()


def reset_password(db: Session, token: str, new_password: str) -> None:
    user = repo.consume_password_reset(db, token, hash_password(new_password))
    if user is None:
        raise InvalidTokenException()
    # A password reset invalidates every existing refresh session.
    repo.revoke_all_sessions(db, user.id)


def verify_email(db: Session, token: str, device_id: str | None = None) -> dict:
    user = repo.consume_email_verification(db, token)
    if user is None:
        raise InvalidTokenException()
    tokens = _issue_tokens(db, user, device_id=device_id)
    return tokens


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise ForbiddenException("Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    repo.revoke_all_sessions(db, user.id)


# ---------------------------------------------------------------------------
# Email change (secure flow)
# ---------------------------------------------------------------------------


def request_email_change(
    db: Session,
    user: User,
    payload: RequestEmailChangeRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RequestEmailChangeResponse:
    if not verify_password(payload.current_password, user.hashed_password):
        audit_logger.log(AuditEvent(
            actor_id=user.id,
            action="email_change_request_failed",
            domain="users",
            resource_type="user",
            resource_id=str(user.id),
            details={"reason": "invalid_password"},
            ip_address=ip_address,
            user_agent=user_agent,
        ))
        raise ForbiddenException("Current password is incorrect")

    new_email = validate_email(payload.new_email)
    if new_email is None:
        raise ForbiddenException("Invalid email format")

    if new_email == user.email:
        raise ForbiddenException("New email must be different from your current email")

    existing = repo.get_user_by_email(db, new_email)
    if existing is not None and existing.id != user.id:
        audit_logger.log(AuditEvent(
            actor_id=user.id,
            action="email_change_request_blocked",
            domain="users",
            resource_type="user",
            resource_id=str(user.id),
            details={"reason": "email_in_use", "target_email": new_email},
            ip_address=ip_address,
            user_agent=user_agent,
        ))
        raise EmailTakenException()

    repo.cancel_pending_email_change(db, user.id)
    raw_code, pending = repo.create_pending_email_change(db, user.id, new_email)

    send_email(
        new_email,
        "Verify your new Mizan email",
        email_change_request_html(raw_code, user.first_name or user.username, new_email),
    )
    send_email(
        user.email,
        "Email change requested for Mizan",
        email_change_notification_html(user.email, new_email, user.first_name or user.username),
    )

    audit_logger.log(AuditEvent(
        actor_id=user.id,
        action="email_change_requested",
        domain="users",
        resource_type="pending_email_change",
        resource_id=str(pending.id),
        details={"new_email": new_email},
        ip_address=ip_address,
        user_agent=user_agent,
    ))

    return RequestEmailChangeResponse()


def confirm_email_change(
    db: Session,
    user: User,
    raw_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    pending = get_pending_email_change_by_token(db, raw_token)
    if pending is None or pending.user_id != user.id:
        audit_logger.log(AuditEvent(
            actor_id=user.id,
            action="email_change_confirm_failed",
            domain="users",
            resource_type="pending_email_change",
            details={"reason": "invalid_or_expired_token"},
            ip_address=ip_address,
            user_agent=user_agent,
        ))
        raise InvalidTokenException()

    old_email = user.email
    updated_user = repo.confirm_pending_email_change(db, pending)
    repo.revoke_all_sessions(db, user.id)

    access_token = create_access_token({"sub": str(updated_user.id)})
    refresh_token = repo.create_session(db, updated_user.id)

    _send_email_change_confirmed(new_email=updated_user.email, user_name=updated_user.first_name or updated_user.username)

    audit_logger.log(AuditEvent(
        actor_id=updated_user.id,
        action="email_change_confirmed",
        domain="users",
        resource_type="user",
        resource_id=str(updated_user.id),
        details={"old_email": old_email, "new_email": updated_user.email},
        ip_address=ip_address,
        user_agent=user_agent,
    ))

    return access_token, refresh_token


def _send_email_change_notification(old_email: str, new_email: str, user_name: str | None) -> None:
    send_email(
        old_email,
        "Email change requested for Mizan",
        email_change_notification_html(old_email, new_email, user_name),
    )


def _send_email_change_confirmed(new_email: str, user_name: str | None) -> None:
    send_email(
        new_email,
        "Your Mizan email has been updated",
        email_change_confirmed_html(new_email, user_name),
    )


def cancel_email_change(db: Session, user: User) -> None:
    count = repo.cancel_pending_email_change(db, user.id)
    if count == 0:
        raise ResourceNotFoundException("No pending email change found")


def get_pending_email_change_status(db: Session, user: User) -> PendingEmailChangeResponse | None:
    pending = repo.get_pending_email_change(db, user.id)
    if pending is None:
        return None
    return PendingEmailChangeResponse(
        id=pending.id,
        new_email=pending.new_email,
        expires_at=pending.expires_at.isoformat() if pending.expires_at else None,
        created_at=pending.created_at.isoformat() if pending.created_at else None,
    )


# ---------------------------------------------------------------------------
# Resend verification
# ---------------------------------------------------------------------------


def resend_verification(
    db: Session, current_user: User, payload: ResendVerificationRequest
) -> dict:
    email = validate_email(payload.email) if payload.email else current_user.email
    user = repo.get_user_by_email(db, email)
    if user is None or user.deleted_at is not None:
        return {"message": "If an account with that email exists and is not verified, a new verification code has been sent."}
    if user.email_verified:
        raise BusinessRuleException("Email is already verified")
    raw_token = repo.create_email_verification(db, user.id)
    send_verification_email(user.email, raw_token, user.first_name or user.username)
    return {"message": "If an account with that email exists and is not verified, a new verification code has been sent."}


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
    email = data.get("email", "").lower()
    email_verified = data.get("email_verified") == "true"
    token_audience = data.get("aud")

    if not google_id or not email:
        raise GoogleOAuthException("Google token missing required fields")

    if not email_verified:
        raise GoogleOAuthException("Google email is not verified")

    if not settings.GOOGLE_CLIENT_ID or token_audience != settings.GOOGLE_CLIENT_ID:
        raise InvalidTokenException("Google ID token audience mismatch")

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
        if user.google_id is None:
            link_google_account(db, user, google_id)
    return _issue_tokens(db, user)
