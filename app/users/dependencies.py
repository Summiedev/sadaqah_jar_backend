"""Dependencies owned by the Authentication and User Identity feature."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import API_V1_PREFIX
from app.core.security import decode_access_token
from app.core.rate_limit import check_rate_limit_key
from app.db.deps import get_db
from app.users.exceptions import InvalidTokenException
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        user_id = int(subject) if subject is not None else None
        token_version = int(payload.get("ver", 0))
    except (JWTError, TypeError, ValueError):
        raise InvalidTokenException()

    user = db.get(User, user_id)
    if (
        user is None
        or user.deleted_at is not None
        or token_version != user.token_version
    ):
        raise InvalidTokenException()

    user.last_active = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def enforce_auth_rate_limit(
    request: Request,
    action: str,
    limit: int = 20,
    period: int = 60,
    *,
    key_suffix: str | None = None,
) -> None:
    """Apply a small, Redis-backed limit to sensitive auth operations.

    Fails CLOSED: if Redis is unreachable the request is denied (429) rather
    than allowed, so an outage cannot silently disable brute-force protection
    on login/register/verify/reset. ``key_suffix`` lets callers scope the
    limit to a specific target (e.g. the email/code being verified) in
    addition to the client IP.
    """
    host = request.client.host if request.client else "unknown"
    key = f"auth:{action}:{host}"
    if key_suffix:
        key = f"{key}:{key_suffix}"
    if not check_rate_limit_key(key, limit=limit, period=period, fail_open=False):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again shortly.",
        )
