# app/services/family_service.py
from datetime import timedelta, date
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog

def update_family_streak_on_contribution(db, jar_id: int, today: date):
    jar = db.query(FamilyJar).filter(FamilyJar.id == jar_id).first()
    if not jar:
        return

    yesterday = today - timedelta(days=1)

    # check if any contribution was on `today` already — if so nothing to do
    if jar.last_activity_date == today:
        return

    # if last activity was yesterday -> increment, else reset to 1
    if jar.last_activity_date == yesterday:
        jar.streak_days += 1
    else:
        jar.streak_days = 1

    if jar.streak_days > jar.longest_streak:
        jar.longest_streak = jar.streak_days

    jar.last_activity_date = today
    db.commit()