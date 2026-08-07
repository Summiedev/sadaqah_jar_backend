"""Prayer-time retrieval and normalization for reminder scheduling."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings


class PrayerTimeLookupError(RuntimeError):
    """Raised when prayer times cannot be obtained or validated."""


@dataclass(frozen=True)
class PrayerTimes:
    fajr: datetime
    sunrise: datetime
    duha_start: datetime
    duha_end: datetime
    zuhr: datetime
    asr: datetime
    maghrib: datetime
    isha: datetime

    def for_anchor(self, anchor: str) -> datetime:
        try:
            return getattr(self, anchor.lower())
        except AttributeError as exc:
            raise ValueError(f"Unsupported prayer-time anchor: {anchor}") from exc


def _parse_clock(value: str, local_date: date, timezone_name: str) -> datetime:
    # Aladhan values may include an offset annotation, e.g. "05:21 (WAT)".
    clock = value.split(" ", 1)[0]
    try:
        parsed = datetime.strptime(clock, "%H:%M").time()
    except ValueError as exc:
        raise PrayerTimeLookupError(f"Invalid prayer-time value: {value!r}") from exc
    return datetime.combine(local_date, parsed, tzinfo=ZoneInfo(timezone_name))


def get_prayer_times(
    latitude: float, longitude: float, local_date: date, timezone_name: str
) -> PrayerTimes:
    """Return location-specific prayer times in the user's local timezone.

    Aladhan is keyless; its calculation method remains configurable because
    communities can reasonably follow different conventions.
    """
    try:
        ZoneInfo(timezone_name)
    except Exception as exc:
        raise PrayerTimeLookupError(f"Invalid IANA timezone: {timezone_name}") from exc

    try:
        response = httpx.get(
            "https://api.aladhan.com/v1/timings",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "date": local_date.strftime("%d-%m-%Y"),
                "method": settings.PRAYER_CALCULATION_METHOD,
            },
            timeout=settings.PRAYER_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        timings = response.json()["data"]["timings"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise PrayerTimeLookupError(
            "Unable to retrieve prayer times from Aladhan"
        ) from exc

    fajr = _parse_clock(timings["Fajr"], local_date, timezone_name)
    sunrise = _parse_clock(timings["Sunrise"], local_date, timezone_name)
    zuhr = _parse_clock(timings["Dhuhr"], local_date, timezone_name)
    return PrayerTimes(
        fajr=fajr,
        sunrise=sunrise,
        # A conservative window: 15 minutes after sunrise until shortly before Zuhr.
        duha_start=sunrise + timedelta(minutes=15),
        duha_end=zuhr - timedelta(minutes=10),
        zuhr=zuhr,
        asr=_parse_clock(timings["Asr"], local_date, timezone_name),
        maghrib=_parse_clock(timings["Maghrib"], local_date, timezone_name),
        isha=_parse_clock(timings["Isha"], local_date, timezone_name),
    )
