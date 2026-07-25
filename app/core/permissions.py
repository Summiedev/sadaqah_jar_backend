"""Permission registry and evaluator."""

from dataclasses import dataclass
from typing import Callable

from app.users.models import User


@dataclass
class Permission:
    key: str
    description: str
    evaluator: Callable[[User], bool] | None = None


_PERMISSIONS: dict[str, Permission] = {}


def register_permission(permission: Permission) -> None:
    _PERMISSIONS[permission.key] = permission


def require_permission(user: User, permission_key: str) -> bool:
    permission = _PERMISSIONS.get(permission_key)
    if permission is None:
        return False
    if permission.evaluator is None:
        return user.role == "ADMIN"
    return permission.evaluator(user)


def get_registered_permissions() -> list[Permission]:
    return list(_PERMISSIONS.values())
