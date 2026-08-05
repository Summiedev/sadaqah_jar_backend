"""Resolve data-backed content for editable notification templates."""

import json
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.adhkar import Adhkar, TimeOfDay
from app.notifications.models import NotificationTemplate, ScheduledNotification
from app.services.personalization_service import generate_personalized_acts
from app.services.reminder_library import (
    get_entries_for_source,
    get_random_entry,
)


class _FormatValues(defaultdict):
    def __missing__(self, key):
        return ""


def _config(value: str | None) -> dict:
    try:
        parsed = json.loads(value) if value else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def resolve_reminder_content(
    db: Session, schedule: ScheduledNotification, template: NotificationTemplate
) -> tuple[str, str]:
    """Render an editable template using the source declared in its config."""
    config = _config(template.strategy_config)
    values: dict[str, str] = {}
    source = config.get("content_source")

    if source in {"morning_adhkar", "evening_adhkar"}:
        time_of_day = TimeOfDay.morning if source == "morning_adhkar" else TimeOfDay.evening
        adhkar = (
            db.query(Adhkar)
            .filter(Adhkar.time_of_day == time_of_day)
            .order_by(func.random())
            .first()
        )
        if adhkar:
            values = {
                "arabic": adhkar.text_arabic,
                "translation": adhkar.text_translation,
                "source": adhkar.source,
                "repeat_count": str(adhkar.repeat_count),
            }
    elif source == "personalized_sadaqah":
        acts = generate_personalized_acts(db, schedule.user_id)
        if acts:
            act = acts[schedule.id % len(acts)]
            values = {"act_title": act.title, "act_description": act.description}
    elif source == "rotating_messages":
        messages = config.get("messages", [])
        if isinstance(messages, list) and messages:
            values = {"message": str(messages[schedule.id % len(messages)])}
    else:
        # Use the expanded reminder library for random content selection.
        entry = get_random_entry(source)
        if entry is not None:
            values = {
                "title": entry.title,
                "message": entry.message,
                "source": entry.source,
            }

    formatter = _FormatValues(str, values)
    return (
        template.title_template.format_map(formatter),
        template.message_template.format_map(formatter),
    )