from datetime import datetime
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog
from app.models.family_jar_member import FamilyJarMember
from app.services.badge_service import give_user_badge


def update_family_streak(db, jar_id: int):
    today = datetime.utcnow().date()

    today_logs = (
        db.query(FamilyJarLog)
        .filter(FamilyJarLog.family_jar_id == jar_id, FamilyJarLog.date == today)
        .count()
    )

    if today_logs == 0:
        return False  # no streak continuation

    return True


def check_family_badges(db, jar_id: int):
    jar = db.query(FamilyJar).filter(FamilyJar.id == jar_id).first()
    if not jar:
        return

    # Award to all members when the family streak hits a milestone
    member_ids = [
        row.user_id
        for row in db.query(FamilyJarMember.user_id)
        .filter(FamilyJarMember.family_jar_id == jar_id)
        .all()
    ]

    if jar.group_current_streak >= 7:
        for uid in member_ids:
            give_user_badge(db, uid, "Family 7-Day Streak")

    if jar.group_current_streak >= 30:
        for uid in member_ids:
            give_user_badge(db, uid, "Family 30-Day Streak")
