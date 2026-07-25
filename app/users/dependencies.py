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
        subject = decode_access_token(token).get("sub")
        user_id = int(subject) if subject is not None else None
    except (JWTError, TypeError, ValueError):
        raise InvalidTokenException()

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise InvalidTokenException()

    user.last_active = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def enforce_auth_rate_limit(request: Request, action: str, limit: int = 20) -> None:
    """Apply a small, Redis-backed limit to unauthenticated auth operations."""
    host = request.client.host if request.client else "unknown"
    if not check_rate_limit_key(f"auth:{action}:{host}", limit=limit, period=60):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again shortly.",
        )
