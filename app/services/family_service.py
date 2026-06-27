from datetime import date, timedelta

from app.models.family_jar import FamilyJar


def update_family_streak_on_contribution(jar: FamilyJar, today: date) -> bool:
    yesterday = today - timedelta(days=1)

    if jar.last_activity_date == today:
        return False

    if jar.last_activity_date == yesterday:
        jar.streak_days = (jar.streak_days or 0) + 1
    else:
        jar.streak_days = 1

    jar.longest_streak = max(jar.longest_streak or 0, jar.streak_days)
    jar.last_activity_date = today
    return True
