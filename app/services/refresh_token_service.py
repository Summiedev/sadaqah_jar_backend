import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_BYTES = 32


def hash_refresh_token(raw_token: str) -> str:
    """Hash a refresh token before lookup/storage.

    Raw refresh tokens are bearer credentials and must never be persisted.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_refresh_token(db: Session, user_id: int) -> str:
    """Create and persist a hashed refresh token, returning only the raw token once."""
    raw_token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    db.add(
        RefreshToken(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )
    )
    db.commit()

    return raw_token


def get_valid_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    token_hash = hash_refresh_token(raw_token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .first()
    )


def revoke_refresh_token(db: Session, token: RefreshToken) -> None:
    token.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(token)
    db.commit()


def rotate_refresh_token(db: Session, token: RefreshToken) -> str:
    """Revoke the used refresh token and mint a replacement.

    This enforces revoke-on-use to limit token theft/replay windows.
    """
    user_id = token.user_id
    revoke_refresh_token(db, token)
    return create_refresh_token(db, user_id)
