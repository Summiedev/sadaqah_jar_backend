from fastapi import Depends

from app.users.dependencies import get_current_user
from app.users.exceptions import ForbiddenException
from app.users.models import Role, User


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Authorization dependency: only ADMIN users may proceed."""
    if current_user.role != Role.ADMIN:
        raise ForbiddenException("Admin privileges required")
    return current_user
