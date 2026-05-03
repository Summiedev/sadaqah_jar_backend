from datetime import datetime, timedelta
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog

def update_family_streak(db, jar_id: int):
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    today_logs = db.query(FamilyJarLog).filter(
        FamilyJarLog.family_jar_id == jar_id,
        FamilyJarLog.date == today
    ).count()

    if today_logs == 0:
        return False  # no streak continuation

    return True
def check_family_badges(db, jar_id: int):
    jar = db.query(FamilyJar).filter(FamilyJar.id == jar_id).first()

    if jar.group_current_streak >= 7:
        # award 7-day badge
        pass

    if jar.group_current_streak >= 30:
        # award 30-day badge
        pass