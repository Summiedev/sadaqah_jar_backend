"""Registry combining all reminder content categories."""

import random

from app.services.reminder_library.base import ReminderEntry
from app.services.reminder_library.prayer import PRAYER_FARDH, PRAYER_NAFL
from app.services.reminder_library.adhkar_morning import ADHKAR_MORNING
from app.services.reminder_library.adhkar_evening import ADHKAR_EVENING
from app.services.reminder_library.time_based import TIME_BASED
from app.services.reminder_library.quran import QURAN
from app.services.reminder_library.hadith import HADITH
from app.services.reminder_library.reflection import REFLECTION
from app.services.reminder_library.hereafter import HEREAFTER
from app.services.reminder_library.good_deeds import GOOD_DEEDS
from app.services.reminder_library.quotes import QUOTES

# Category → entries mapping
LIBRARY: dict[str, list[ReminderEntry]] = {
    "prayer_fardh": PRAYER_FARDH,
    "prayer_nafl": PRAYER_NAFL,
    "adhkar_morning": ADHKAR_MORNING,
    "adhkar_evening": ADHKAR_EVENING,
    "time_based": TIME_BASED,
    "quran": QURAN,
    "hadith": HADITH,
    "reflection": REFLECTION,
    "hereafter": HEREAFTER,
    "good_deeds": GOOD_DEEDS,
    "quotes": QUOTES,
}

# Mapping of template content sources to library category keys.
SOURCE_TO_CATEGORY: dict[str, str] = {
    "prayer_fardh": "prayer_fardh",
    "prayer_nafl": "prayer_nafl",
    "adhkar_morning": "adhkar_morning",
    "adhkar_evening": "adhkar_evening",
    "time_based": "time_based",
    "quran": "quran",
    "quran_ayah": "quran",
    "hadith": "hadith",
    "reflection": "reflection",
    "reflection_prompt": "reflection",
    "hereafter": "hereafter",
    "good_deeds": "good_deeds",
    "quotes": "quotes",
}

# Count of all entries for statistics.
TOTAL_ENTRIES = sum(len(entries) for entries in LIBRARY.values())


def get_entries_for_source(source: str) -> list[ReminderEntry]:
    """Return the entry list for a template content source."""
    category = SOURCE_TO_CATEGORY.get(source)
    if category is None:
        return []
    return LIBRARY.get(category, [])


def get_random_entry(source: str, *, exclude: set[int] | None = None) -> ReminderEntry | None:
    """Return a random entry for a content source, avoiding excluded indices when possible."""
    entries = get_entries_for_source(source)
    if not entries:
        return None
    if exclude:
        candidates = [
            (idx, entry) for idx, entry in enumerate(entries) if idx not in exclude
        ]
        if candidates:
            return random.choice(candidates)[1]
    return random.choice(entries)


def get_entry_count(source: str) -> int:
    """Return the number of entries available for a content source."""
    return len(get_entries_for_source(source))