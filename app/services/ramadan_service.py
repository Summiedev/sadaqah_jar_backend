# app/services/ramadan_service.py
from datetime import date, timedelta

# Configure these from settings in production
RAMADAN_START = date(2026, 2, 18)
RAMADAN_END = date(2026, 3, 19)

def is_ramadan(today: date | None = None) -> bool:
    if today is None:
        today = date.today()
    return RAMADAN_START <= today <= RAMADAN_END

def is_last_10_nights(today: date | None = None) -> bool:
    if today is None:
        today = date.today()
    if not is_ramadan(today):
        return False
    # last 10 nights = last 10 days of Ramadan inclusive
    return today >= (RAMADAN_END - timedelta(days=9))