from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.exceptions import ResourceNotFoundException
from app.users import repository as repo
from app.users import service
from app.users.dependencies import enforce_auth_rate_limit, get_current_user
from app.users.models import User
from app.users.repository import hash_refresh_token
from app.emails.templates import email_change_request_html
from app.services.email_service import send_email
from app.users.schemas import (
    AvatarUpdate,
    ChangePasswordRequest,
    ConfirmEmailChangeRequest,
    ConfirmEmailChangeResponse,
    DeviceResponse,
    DeviceUpdate,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    PendingEmailChangeResponse,
    PushTokenRequest,
    RefreshRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    RequestEmailChangeRequest,
    RequestEmailChangeResponse,
    SessionResponse,
    TokenResponse,
    VerifyEmailOtpRequest,
    UserLogin,
    UserModeUpdate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserRegister,
)

router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
DeviceId = Annotated[str | None, Header(alias="X-Device-Id")]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@auth_router.post("/register", response_model=TokenResponse)
def register(
    payload: UserRegister, request: Request, db: DbDep, device_id: DeviceId = None
):
    enforce_auth_rate_limit(request, "register")
    return service.register(db, payload, device_id=device_id)


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: DbDep, device_id: DeviceId = None):
    enforce_auth_rate_limit(request, "login")
    return service.login(db, payload.email, payload.password, device_id=device_id)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbDep, device_id: DeviceId = None):
    return service.refresh(db, payload.refresh_token, device_id=device_id)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DbDep):
    service.logout(db, payload.refresh_token)


@auth_router.get("/verify-email", response_model=TokenResponse)
def verify_email(request: Request, db: DbDep, token: str = Query(...)):
    # Throttle per-IP AND per-code so a 6-digit OTP cannot be brute-forced.
    # Fails closed (see enforce_auth_rate_limit): a Redis outage denies rather
    # than opening the whole code space.
    enforce_auth_rate_limit(
        request, "verify-email", limit=5, period=900, key_suffix=token
    )
    tokens = service.verify_email(db, token)

    return tokens


@auth_router.post("/verify-email", response_model=TokenResponse)
def verify_email_otp(
    payload: VerifyEmailOtpRequest,
    request: Request,
    db: DbDep,
    device_id: DeviceId = None,
):
    # Fail-closed throttle so the 6-digit OTP space cannot be exhausted.
    enforce_auth_rate_limit(
        request, "verify-email", limit=5, period=900, key_suffix=payload.code
    )
    return service.verify_email(db, payload.code, device_id=device_id)


@auth_router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: DbDep):
    enforce_auth_rate_limit(request, "forgot-password")
    return service.forgot_password(db, payload.email)


@auth_router.post("/resend-verification", response_model=ResendVerificationResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: DbDep,
    current_user: User = Depends(get_current_user),
):
    enforce_auth_rate_limit(request, "resend-verification", limit=3, period=900)
    return service.resend_verification(db, current_user, payload)


@auth_router.post("/google", response_model=TokenResponse)
def google_auth(payload: GoogleAuthRequest, db: DbDep):
    return service.google_auth(db, payload)


@auth_router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: DbDep):
    service.reset_password(db, payload.token, payload.new_password)
    return {"message": "Password reset successfully"}


@auth_router.get("/me", response_model=UserProfileResponse)
def get_auth_me(current_user: CurrentUser, db: DbDep):
    """Flutter session bootstrap endpoint; shares the canonical profile service."""
    return service.get_profile(db, current_user)


@auth_router.patch("/me", response_model=UserProfileResponse)
def update_auth_me(payload: UserProfileUpdate, current_user: CurrentUser, db: DbDep):
    return service.update_profile(db, current_user, payload)


@auth_router.patch("/preferences", response_model=UserPreferencesResponse)
def update_auth_preferences(
    payload: UserPreferencesUpdate, current_user: CurrentUser, db: DbDep
):
    return service.update_preferences(db, current_user, payload)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: CurrentUser, db: DbDep):
    return service.get_profile(db, current_user)


@router.patch("/me", response_model=UserProfileResponse)
def update_me(payload: UserProfileUpdate, current_user: CurrentUser, db: DbDep):
    return service.update_profile(db, current_user, payload)


@router.patch("/mode", response_model=UserProfileResponse)
def update_mode(payload: UserModeUpdate, current_user: CurrentUser, db: DbDep):
    return service.update_mode(db, current_user, payload)


@router.patch("/me/avatar", response_model=UserProfileResponse)
def update_avatar(payload: AvatarUpdate, current_user: CurrentUser, db: DbDep):
    return service.update_profile(
        db, current_user, UserProfileUpdate(avatar_data=payload.avatar_data)
    )


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, db: DbDep
):
    service.change_password(db, current_user, payload)


@router.post("/me/email/change-request", response_model=RequestEmailChangeResponse)
def request_email_change(
    payload: RequestEmailChangeRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbDep,
):
    enforce_auth_rate_limit(request, "email-change", limit=5, period=900)
    return service.request_email_change(
        db,
        current_user,
        payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/me/email/confirm", response_model=ConfirmEmailChangeResponse)
def confirm_email_change(
    payload: ConfirmEmailChangeRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbDep,
):
    enforce_auth_rate_limit(
        request, "email-confirm", limit=5, period=900, key_suffix=payload.token
    )
    access, refresh = service.confirm_email_change(
        db,
        current_user,
        payload.token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ConfirmEmailChangeResponse(access_token=access, refresh_token=refresh)


@router.get("/me/email/pending", response_model=PendingEmailChangeResponse | None)
def get_pending_email_change(current_user: CurrentUser, db: DbDep):
    return service.get_pending_email_change_status(db, current_user)


@router.post("/me/email/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_email_change(current_user: CurrentUser, db: DbDep):
    service.cancel_email_change(db, current_user)


@router.post("/me/email/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_email_change_verification(
    request: Request,
    current_user: CurrentUser,
    db: DbDep,
):
    enforce_auth_rate_limit(request, "email-change-resend", limit=3, period=900)
    pending = service.get_pending_email_change_status(db, current_user)
    if pending is None:
        raise ResourceNotFoundException("No pending email change found")
    repo.cancel_pending_email_change(db, current_user.id)
    raw_code = repo.create_pending_email_change(db, current_user.id, pending.new_email)[
        0
    ]
    send_email(
        pending.new_email,
        "Verify your new Mizan email",
        email_change_request_html(
            raw_code,
            current_user.first_name or current_user.username,
            pending.new_email,
        ),
    )


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


@router.get("/me/preferences", response_model=UserPreferencesResponse)
def get_preferences(current_user: CurrentUser, db: DbDep):
    return service.get_preferences(db, current_user)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
def update_preferences(
    payload: UserPreferencesUpdate, current_user: CurrentUser, db: DbDep
):
    return service.update_preferences(db, current_user, payload)


@router.patch("/preferences", response_model=UserPreferencesResponse)
def update_current_user_preferences(
    payload: UserPreferencesUpdate, current_user: CurrentUser, db: DbDep
):
    return service.update_preferences(db, current_user, payload)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/me/sessions", response_model=list[SessionResponse])
def get_sessions(current_user: CurrentUser, db: DbDep, request: Request):
    raw = _extract_refresh(request)
    current_hash = hash_refresh_token(raw) if raw else None
    return service.list_user_sessions(db, current_user, current_hash)


@router.delete("/me/sessions", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(current_user: CurrentUser, db: DbDep):
    service.logout_everywhere(db, current_user)


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def logout_session(session_id: int, current_user: CurrentUser, db: DbDep):
    service.logout_session(db, current_user, session_id)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


@router.get("/me/devices", response_model=list[DeviceResponse])
def get_devices(current_user: CurrentUser, db: DbDep):
    return service.list_user_devices(db, current_user)


@router.post("/me/devices")
def register_device(payload: PushTokenRequest, current_user: CurrentUser, db: DbDep):
    return service.register_push_token(db, current_user, payload)


@router.post("/me/push-token")
def push_token(payload: PushTokenRequest, current_user: CurrentUser, db: DbDep):
    return service.register_push_token(db, current_user, payload)


@router.patch("/me/devices/{device_id}")
def update_device(
    device_id: int, payload: DeviceUpdate, current_user: CurrentUser, db: DbDep
):
    return service.update_user_device(
        db,
        current_user,
        device_id,
        payload.device_name,
        payload.push_token,
        payload.app_version,
    )


@router.delete("/me/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, current_user: CurrentUser, db: DbDep):
    service.delete_user_device(db, current_user, device_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_refresh(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip()
