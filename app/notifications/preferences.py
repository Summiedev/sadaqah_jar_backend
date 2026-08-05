"""Notification preference and quiet-hours enforcement.

This module centralises the rules that decide whether a notification should
be delivered to a user, and if so, whether it should be delayed because the
user is in quiet hours.

Preferences are stored as a JSON document on ``UserPreference.notification_preferences``
with per-category booleans. Quiet hours are stored in the same document as
``{"quiet_hours": {"enabled": true, "start": "22:00", "end": "07:00"}}``.

Frequency is stored as ``{"frequency": "low" | "medium" | "high"}``.
A master toggle is stored as ``{"all_enabled": true}``.
"""

import json
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.users.models import User, UserPreference

# All notification categories supported by the system.
ALL_CATEGORIES = {
    "prayer_fardh",
    "prayer_nafl",
    "adhkar_morning",
    "adhkar_evening",
    "time_based",
    "quran",
    "hadith",
    "reflection",
    "hereafter",
    "good_deeds",
    "quotes",
    "family",
    "journey",
    "prayer",
    "adhkar",
    "reading",
    "charity",
    "islamic_occasions",
    "announcements",
    "security",
    "system",
}


def _load_prefs(prefs: UserPreference | None) -> dict:
    if prefs is None:
        return {}
    try:
        data = json.loads(prefs.notification_preferences or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_reminder_prefs(prefs: UserPreference | None) -> dict:
    if prefs is None:
        return {}
    try:
        data = json.loads(prefs.reminder_preferences or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def is_category_enabled(
    db: Session, user_id: int, category: str, *, channel: str = "push"
) -> bool:
    """Return True if the user has not disabled this category for the channel.

    Defaults to enabled when no preference is stored (opt-out model).
    """
    user = db.get(User, user_id)
    if user is None:
        return False
    prefs = _load_prefs(user.preferences)

    # Master toggle — if user disabled all notifications, nothing goes through.
    if "all_enabled" in prefs and not prefs["all_enabled"]:
        return False

    # Check per-category toggles
    category_prefs = prefs.get("categories", {})
    if isinstance(category_prefs, dict):
        cat = category_prefs.get(category)
        if isinstance(cat, dict):
            return bool(cat.get(channel, True))
        if isinstance(cat, bool):
            return cat
    # Global channel toggle
    channel_key = f"{channel}_enabled"
    if channel_key in prefs:
        return bool(prefs[channel_key])
    return True


def get_frequency(db: Session, user_id: int) -> str:
    """Return the notification frequency preference: low, medium, or high."""
    user = db.get(User, user_id)
    if user is None:
        return "medium"
    prefs = _load_prefs(user.preferences)
    freq = prefs.get("frequency", "medium")
    if freq not in {"low", "medium", "high"}:
        return "medium"
    return freq


def get_quiet_hours(db: Session, user_id: int) -> tuple[time | None, time | None]:
    """Return (start, end) quiet hours for a user, or (None, None) if disabled."""
    user = db.get(User, user_id)
    if user is None:
        return None, None
    prefs = _load_prefs(user.preferences)
    qh = prefs.get("quiet_hours")
    if not isinstance(qh, dict) or not qh.get("enabled"):
        return None, None
    try:
        start = time.fromisoformat(str(qh.get("start", "")))
        end = time.fromisoformat(str(qh.get("end", "")))
    except (ValueError, TypeError):
        return None, None
    return start, end


def is_in_quiet_hours(db: Session, user_id: int, now: datetime | None = None) -> bool:
    """Return True if the current local time falls inside quiet hours."""
    start, end = get_quiet_hours(db, user_id)
    if start is None or end is None:
        return False
    user = db.get(User, user_id)
    tz_name = user.preferences.timezone if user and user.preferences else "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    now = now or datetime.now(tz)
    local_time = now.astimezone(tz).time()
    if start <= end:
        return start <= local_time <= end
    # Overnight window (e.g. 22:00 → 07:00)
    return local_time >= start or local_time <= end


def should_delay_for_quiet_hours(
    db: Session, user_id: int, category: str, now: datetime | None = None
) -> bool:
    """Return True if the notification should be delayed (not dropped).

    Security and system notifications are exempt from quiet hours.
    """
    if category in {"security", "system"}:
        return False
    return is_in_quiet_hours(db, user_id, now=now)


def get_category_state(
    db: Session, user_id: int
) -> dict:
    """Return the full notification preference state for the UI."""
    user = db.get(User, user_id)
    if user is None:
        return {}
    prefs = _load_prefs(user.preferences)
    categories = prefs.get("categories", {})
    if not isinstance(categories, dict):
        categories = {}
    # Default all categories to enabled (opt-out model)
    state = {
        "all_enabled": prefs.get("all_enabled", True),
        "frequency": prefs.get("frequency", "medium"),
        "quiet_hours": prefs.get("quiet_hours", {"enabled": False}),
        "categories": {
            category: bool(categories.get(category, True))
            for category in ALL_CATEGORIES
        },
    }
    return state