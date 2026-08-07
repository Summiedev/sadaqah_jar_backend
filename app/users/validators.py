import re

from app.users.exceptions import ForbiddenException


def validate_username(username: str | None) -> str | None:
    if username is None:
        return None
    stripped = username.strip()
    if not stripped:
        raise ForbiddenException("Username cannot be empty")
    return stripped


def validate_email(email: str | None) -> str | None:
    if email is None:
        return None
    stripped = email.strip().lower()
    if not stripped or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", stripped):
        raise ValueError("Invalid email format")
    return stripped
