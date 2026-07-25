from fastapi import Depends, HTTPException

from app.core.auth import get_current_user
from app.models.user import User
from app.users.models import Role


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
