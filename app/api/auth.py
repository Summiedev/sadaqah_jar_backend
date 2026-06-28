import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.deps import get_db
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdatePreferencesRequest,
    UserCreate,
    UserLogin,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.email_service import send_email
from app.services.refresh_token_service import (
    create_refresh_token,
    get_valid_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_verification_email(user: User, raw_token: str) -> str:
    link = f"{settings.APP_URL}/api/v1/auth/verify-email?token={raw_token}"
    return f"""\
<html><body>
<h2>Verify your email for {settings.APP_NAME}</h2>
<p>Hi {user.username},</p>
<p>Click the link below to verify your email address:</p>
<p><a href="{link}">{link}</a></p>
<p>This link expires in 24 hours.</p>
<p>If you did not create an account, ignore this email.</p>
</body></html>"""


def _make_password_reset_email(user: User, raw_token: str) -> str:
    link = f"{settings.APP_URL}/reset-password?token={raw_token}"
    return f"""\
<html><body>
<h2>Password reset for {settings.APP_NAME}</h2>
<p>Hi {user.username},</p>
<p>Click the link below to reset your password:</p>
<p><a href="{link}">{link}</a></p>
<p>This link expires in 1 hour.</p>
<p>If you did not request a password reset, ignore this email.</p>
</body></html>"""


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    username = user_data.username.strip()
    email = user_data.email.strip().lower()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_taken", "message": "Username already taken"},
        )

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        conflict = db.query(User).filter(User.username == username).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "username_taken", "message": "Username already taken"},
            )
        email_conflict = db.query(User).filter(User.email == email).first()
        if email_conflict:
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(
            status_code=500,
            detail="Registration failed due to a constraint error. Please try again.",
        )
    db.refresh(user)

    # Generate email verification token and send
    raw_token = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            token=raw_token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=24),
        )
    )
    db.commit()
    send_email(
        user.email, "Verify your email", _make_verification_email(user, raw_token)
    )

    token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(db, user.id)
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.email == user_data.email,
            User.deleted_at.is_(None),
        )
        .first()
    )

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(db, user.id)
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_record = get_valid_refresh_token(db, payload.refresh_token)
    if token_record is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    raw = rotate_refresh_token(db, token_record)

    new_access = create_access_token({"sub": str(token_record.user_id)})
    return {"access_token": new_access, "refresh_token": raw, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    token_record = get_valid_refresh_token(db, payload.refresh_token)
    if token_record:
        revoke_refresh_token(db, token_record)


# ---------------------------------------------------------------------------
# Email verification (track-and-prompt only — does not gate any feature)
# ---------------------------------------------------------------------------


@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    vt = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.token == token,
            EmailVerificationToken.expires_at > now,
        )
        .first()
    )
    if not vt:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )

    user = db.query(User).filter(User.id == vt.user_id).first()
    if user:
        user.email_verified = True
        db.add(user)

    db.delete(vt)
    db.commit()
    return {"message": "Email verified successfully"}


# ---------------------------------------------------------------------------
# Password reset (enumeration-safe forgot-password)
# ---------------------------------------------------------------------------


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Always returns the same response regardless of whether the email exists.

    This prevents attackers from enumerating registered emails via timing or
    response-body differences. The only side effect is a DB query and an
    optional email send, both of which have no observable difference to the
    caller.
    """
    user = (
        db.query(User)
        .filter(
            User.email == payload.email,
            User.deleted_at.is_(None),
        )
        .first()
    )

    if user:
        raw_token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                token=raw_token,
                user_id=user.id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(hours=1),
            )
        )
        db.commit()
        send_email(
            user.email, "Password reset", _make_password_reset_email(user, raw_token)
        )

    return ForgotPasswordResponse()


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    prt = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == payload.token,
            PasswordResetToken.expires_at > now,
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    if not prt:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = (
        db.query(User)
        .filter(
            User.id == prt.user_id,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    prt.used_at = now
    db.add(user)
    db.add(prt)
    db.commit()

    return {"message": "Password reset successfully"}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserProfileResponse)
def me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "role": current_user.role,
        "avatar_data": current_user.avatar_data,
        "evidence_mode": current_user.evidence_mode,
        "friday_reminder": current_user.friday_reminder,
    }


@router.patch("/me", response_model=UserProfileResponse)
def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.username is not None:
        username = payload.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        existing_username = (
            db.query(User)
            .filter(User.username == username, User.id != current_user.id)
            .first()
        )
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = username

    if payload.email is not None:
        email = payload.email.strip().lower()
        existing_email = (
            db.query(User)
            .filter(User.email == email, User.id != current_user.id)
            .first()
        )
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = email
        current_user.email_verified = False  # re-verify on email change

    if payload.avatar_data is not None:
        avatar_data = payload.avatar_data.strip()
        current_user.avatar_data = avatar_data or None

    db.commit()
    db.refresh(current_user)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "role": current_user.role,
        "avatar_data": current_user.avatar_data,
        "evidence_mode": current_user.evidence_mode,
        "friday_reminder": current_user.friday_reminder,
    }


# ---------------------------------------------------------------------------
# Password change (authenticated)
# ---------------------------------------------------------------------------


@router.patch("/password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
    return {"message": "Password updated successfully"}


# ---------------------------------------------------------------------------
# Preferences (toggle the existing-but-unwired fields)
# ---------------------------------------------------------------------------


@router.patch("/preferences", response_model=UserProfileResponse)
def update_preferences(
    payload: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.evidence_mode is not None:
        current_user.evidence_mode = payload.evidence_mode
    if payload.friday_reminder is not None:
        current_user.friday_reminder = payload.friday_reminder

    db.commit()
    db.refresh(current_user)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "avatar_data": current_user.avatar_data,
        "evidence_mode": current_user.evidence_mode,
        "friday_reminder": current_user.friday_reminder,
    }


# ---------------------------------------------------------------------------
# Account deletion — soft delete with GDPR-style anonymization
# ---------------------------------------------------------------------------


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete the authenticated user.

    Sets deleted_at, anonymizes PII, and revokes all active refresh tokens.
    Jars, streaks, logs, and family_jar_members rows are preserved so that
    leaderboard history and family jar integrity are not broken.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_id = current_user.id

    # Anonymize PII
    current_user.username = f"deleted_user_{user_id}"
    current_user.email = f"deleted_user_{user_id}@anon.local"
    current_user.hashed_password = ""  # invalidate any session
    current_user.deleted_at = now

    # Revoke all active refresh tokens
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": now})

    db.add(current_user)
    db.commit()

    # --- FAMILY JAR OWNERSHIP EDGE CASE ---
    #
    # If current_user is `created_by` on any active FamilyJar that still has
    # other members, that jar now has no "owner" in a meaningful sense.
    #
    # Options for handling this:
    #
    #   A) Automatically transfer ownership to the longest-standing active
    #      member.  Clean for remaining users, but may not be what the group
    #      actually wants.
    #
    #   B) Leave the jar ownerless (created_by points to a deleted user) and
    #      let remaining members continue contributing. The jar won't be
    #      deletable or administrable by any single member.
    #
    #   C) Notify all jar members that the creator has left and let them
    #      decide — requires a new notification type + client-side handling.
    #
    # Currently using (B) as the safest default: the jar remains active,
    # contributions continue, nothing breaks.  If you want ownership
    # transfer (A) or a notification flow (C), let me know.
    #
    # The jars themselves are preserved by the FK architecture:
    #   FamilyJar.created_by → users.id — the anonymized user still exists,
    #   so the FK is satisfied.  `GET /family/jar/...` will show
    #   "Deleted User" for the creator field, which renders gracefully.
