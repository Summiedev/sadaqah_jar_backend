"""
Hijri (Islamic) calendar service using the hijri-converter library.

If the library is unavailable or raises, falls back to hardcoded date ranges
and logs a warning — never let a calendar exception crash a Ramadan/Friday
multiplier calculation, which is core to the reward loop.
"""

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Hardcoded fallback for 2026 CE / 1447-1448 AH
# These are used ONLY when the library call fails.
_FALLBACK_RAMADAN_START = date(2026, 2, 18)
_FALLBACK_RAMADAN_END = date(2026, 3, 19)

_import_warning_shown = False


def _get_hijri_date(gregorian: date) -> tuple[int, int, int] | None:
    """
    Return (year, month, day) in the Hijri calendar, or None on failure.

    The Hijri day starts at sunset, so a date-based conversion has ~1 day
    uncertainty. This is acceptable for Ramadan detection; the exact start
    of Ramadan is always confirmed by moon sighting regardless.
    """
    global _import_warning_shown
    try:
        from hijri_converter import Hijri, Gregorian as _  # noqa: F401

        hijri = Hijri(gregorian.year, gregorian.month, gregorian.day, strict=False)
        # Strict=False means overflow days are clamped rather than raising.
        return (hijri.year, hijri.month, hijri.day)
    except ImportError:
        if not _import_warning_shown:
            logger.warning(
                "hijri-converter not installed. Falling back to hardcoded Ramadan dates. "
                "Install with: pip install hijri-converter"
            )
            _import_warning_shown = True
        return None
    except ValueError as exc:
        # strict=False still raises on some edge dates (e.g. out of range)
        logger.warning("hijri-converter ValueError for %s: %s — using fallback", gregorian, exc)
        return None
    except Exception as exc:
        logger.warning("hijri-converter raised %s for %s — using fallback", type(exc).__name__, gregorian)
        return None


def get_hijri_date(gregorian: date) -> tuple[int, int, int] | None:
    """Public wrapper. Returns (year, month, day) or None."""
    return _get_hijri_date(gregorian)


def is_ramadan(gregorian: date | None = None) -> bool:
    """Check if a Gregorian date falls in Ramadan.

    Uses the real Hijri calendar via hijri-converter.
    Falls back to hardcoded 2026 dates if the library fails.
    """
    if gregorian is None:
        gregorian = date.today()

    hijri = _get_hijri_date(gregorian)
    if hijri is None:
        # Fallback path — log already emitted by _get_hijri_date
        return _FALLBACK_RAMADAN_START <= gregorian <= _FALLBACK_RAMADAN_END

    return hijri[1] == 9  # Ramadan is month 9 in the Hijri calendar


def is_last_10_nights(gregorian: date | None = None) -> bool:
    """Check if a date falls in the last 10 nights of Ramadan.

    Uses the real Hijri calendar. Falls back to hardcoded dates.
    """
    if gregorian is None:
        gregorian = date.today()

    if not is_ramadan(gregorian):
        return False

    hijri = _get_hijri_date(gregorian)
    if hijri is None:
        # Fallback: last 10 days of the hardcoded range
        return gregorian >= (_FALLBACK_RAMADAN_END - timedelta(days=9))

    return hijri[2] >= 21  # Night 21 onwards