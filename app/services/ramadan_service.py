"""
Ramadan date detection — delegates to the Hijri calendar service.

The hardcoded constants are retained as a documented fallback path only.
See hijri_service.py for the fallback logic.
"""

from datetime import date

from app.services.hijri_service import is_last_10_nights as _hijri_last10
from app.services.hijri_service import is_ramadan as _hijri_is_ramadan

# These constants are no longer used directly by this service.
# They are retained here for reference / manual override in extreme edge cases.
# Production callers should use the functions below, which delegate to
# hijri-converter and only fall back to these if the library fails.
RAMADAN_START = date(2026, 2, 18)
RAMADAN_END = date(2026, 3, 19)


def is_ramadan(today: date | None = None) -> bool:
    """Returns True if today (or the given date) falls in Ramadan.

    Delegates to hijri_service which uses the real Hijri calendar.
    Falls back to hardcoded dates if the conversion library is unavailable.
    """
    return _hijri_is_ramadan(today)


def is_last_10_nights(today: date | None = None) -> bool:
    """Returns True if today falls in the last 10 nights of Ramadan.

    Delegates to hijri_service which uses the real Hijri calendar.
    """
    return _hijri_last10(today)
