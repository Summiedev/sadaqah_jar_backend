"""Resolve data-backed content for editable notification templates."""

import json
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.adhkar import Adhkar, TimeOfDay
from app.notifications.models import NotificationTemplate, ScheduledNotification
from app.services.personalization_service import generate_personalized_acts
from app.services.reminder_library import (
    get_random_entry,
)


class _FormatValues(defaultdict):
    def __missing__(self, key):
        return ""


_GENTLE_COPY = {
    "fajr_reminder": (
        ("Time for Fajr", "Begin your day by standing before Allah."),
        ("Fajr is here", "Take a quiet moment to meet your Lord."),
        ("A new day begins", "Let your first pause be with Allah."),
    ),
    "dhuhr_reminder": (
        ("Time for Dhuhr", "Step away for a few minutes and return to Allah."),
        ("A midday pause", "Let Dhuhr bring a little calm to your day."),
        ("Dhuhr is here", "Make space for your prayer, then continue gently."),
    ),
    "asr_reminder": (
        ("Time for Asr", "Pause the afternoon and turn your heart to Allah."),
        ("Asr is here", "Keep a little room in your day for prayer."),
        ("An afternoon pause", "Take a few moments for your meeting with Allah."),
    ),
    "maghrib_reminder": (
        ("Time for Maghrib", "Welcome the evening with gratitude and prayer."),
        ("Maghrib is here", "Pause as the day turns, and stand before Allah."),
        ("A moment at sunset", "Let prayer be part of your evening's beginning."),
    ),
    "isha_reminder": (
        ("Time for Isha", "Close the day with a few moments of prayer."),
        ("Isha is here", "End the day by turning gently back to Allah."),
        ("An evening pause", "Make room for Isha before you rest."),
    ),
    "pre_fajr": (("Fajr is approaching", "Prepare gently for your first prayer of the day."),),
    "pre_dhuhr": (("Dhuhr is approaching", "A midday pause is nearly here."),),
    "pre_maghrib": (("Maghrib is approaching", "The day is turning toward evening prayer."),),
    "pre_isha": (("Isha is approaching", "Prepare for a quiet close to the day."),),
    "morning_adhkar": (
        ("Start Your Morning With Dhikr", "Take a few peaceful moments for your Morning Adhkar."),
        ("Remember Allah This Morning", "Begin the day with the remembrance that steadies the heart."),
        ("A Morning Moment of Dhikr", "Make a little space for your morning remembrance."),
    ),
    "morning_adhkar_expanded": (
        ("Start Your Morning With Dhikr", "Take a few peaceful moments for your Morning Adhkar."),
        ("Remember Allah This Morning", "Begin the day with the remembrance that steadies the heart."),
        ("A Morning Moment of Dhikr", "Make a little space for your morning remembrance."),
    ),
    "evening_adhkar": (
        ("Let Your Evening Begin With Dhikr", "Take a quiet moment for your Evening Adhkar."),
        ("Remember Allah This Evening", "Settle into the evening with a little remembrance."),
        ("An Evening Moment of Dhikr", "Make a peaceful pause for your evening remembrance."),
    ),
    "evening_adhkar_expanded": (
        ("Let Your Evening Begin With Dhikr", "Take a quiet moment for your Evening Adhkar."),
        ("Remember Allah This Evening", "Settle into the evening with a little remembrance."),
        ("An Evening Moment of Dhikr", "Make a peaceful pause for your evening remembrance."),
    ),
    "quran_reminder": (
        ("A Moment With the Quran", "You haven't read Quran today. Take a few minutes for a page or two."),
        ("A Page With the Quran", "A little time with the Quran can bring your day back into focus."),
        ("Make Room for Quran", "If you have a moment, open the Quran and read at your own pace."),
    ),
    "quran_verse": (
        ("A Moment With the Quran", "You haven't read Quran today. Take a few minutes for a page or two."),
        ("A Page With the Quran", "A little time with the Quran can bring your day back into focus."),
        ("Make Room for Quran", "If you have a moment, open the Quran and read at your own pace."),
    ),
    "reflection_prompt": (
        ("A Moment to Reflect", "Make a little space to notice what is on your heart."),
        ("A Quiet Check-In", "Pause, take a breath, and write one honest line."),
        ("Leave Room for Reflection", "A few thoughtful words can help you carry the day with care."),
    ),
    "tahajjud_reminder": (
        ("A Quiet Night Prayer", "If you are awake, take a moment for dua or Tahajjud."),
        ("A Still Moment With Allah", "The quiet of night can make room for a heartfelt dua."),
    ),
    "witr_reminder": (
        ("Remember Witr", "If it is part of your practice, make room for Witr before rest."),
        ("A Gentle Night Reminder", "Close your evening with Witr when you are ready."),
    ),
    "witr_reminder_expanded": (
        ("Remember Witr", "If it is part of your practice, make room for Witr before rest."),
        ("A Gentle Night Reminder", "Close your evening with Witr when you are ready."),
    ),
    "salatul_duha": (
        ("A Moment for Duha", "If you can, take a little time for the Duha prayer."),
        ("Duha, When You Can", "A quiet two rak'ahs can be a gentle pause in your morning."),
    ),
    "duha_reminder": (
        ("A Moment for Duha", "If you can, take a little time for the Duha prayer."),
        ("Duha, When You Can", "A quiet two rak'ahs can be a gentle pause in your morning."),
    ),
    "nawafil_after_dhuhr": (
        ("A Quiet Moment for Nawafil", "If it suits your day, take a few minutes for voluntary prayer after Dhuhr."),
        ("After Dhuhr", "There is room for a little extra prayer, whenever you feel ready."),
    ),
    "nawafil_after_maghrib": (
        ("A Quiet Moment for Nawafil", "If it suits your day, take a few minutes for voluntary prayer after Maghrib."),
        ("After Maghrib", "A little extra prayer can be a peaceful way to begin the evening."),
    ),
    "nawafil_after_isha": (
        ("A Quiet Moment for Nawafil", "If it suits your day, take a few minutes for voluntary prayer after Isha."),
        ("After Isha", "Make room for a little extra prayer before settling into the night."),
    ),
}


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
    copy_options = _GENTLE_COPY.get(template.key)
    if copy_options:
        title, message = copy_options[schedule.id % len(copy_options)]
        return title, message

    values: dict[str, str] = {}
    source = config.get("content_source")

    if source in {"morning_adhkar", "evening_adhkar"}:
        time_of_day = (
            TimeOfDay.morning if source == "morning_adhkar" else TimeOfDay.evening
        )
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
