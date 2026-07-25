"""Sadaqah domain validators."""

from app.sadaqah.models import ActivityType, ActivityContext


def validate_activity_type(value: str) -> ActivityType:
    try:
        return ActivityType(value)
    except ValueError:
        raise ValueError(f"Invalid activity type: {value}")


def validate_activity_context(value: str) -> ActivityContext:
    try:
        return ActivityContext(value)
    except ValueError:
        raise ValueError(f"Invalid activity context: {value}")


def validate_note(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > 500:
        raise ValueError("Note must be 500 characters or fewer")
    return stripped


def validate_duration_seconds(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("Duration must be non-negative")
    if value > 86400:
        raise ValueError("Duration cannot exceed 24 hours")
    return value
