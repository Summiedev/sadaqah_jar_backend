import random
from datetime import datetime

from sqlalchemy import func

from app.core.cache import cache_daily_acts
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.adhkar import Adhkar, TimeOfDay
from app.models.family_jar_member import FamilyJarMember
from app.models.notification import Notification
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.services.analytics_service import compute_weekly_stats
from app.services.notification_service import create_notification
from app.services.personalization_service import generate_personalized_acts
from app.services.ramadan_service import is_ramadan
from app.services.streak_service import validate_streak


@celery_app.task
def generate_daily_acts():
    db = SessionLocal()
    try:
        candidate_query = db.query(SadaqahAct).filter(SadaqahAct.verified == True)
        if not is_ramadan():
            candidate_query = candidate_query.filter(SadaqahAct.is_ramadan_only == False)

        candidate_acts = candidate_query.all()

        active_user_ids = [row[0] for row in db.query(User.id).filter(User.is_active == True).all()]

        for user_id in active_user_ids:
            daily_acts = generate_personalized_acts(db, user_id, acts=candidate_acts)
            cache_daily_acts(
                user_id,
                [
                    {
                        "id": act.id,
                        "title": act.title,
                        "category": act.category,
                        "difficulty": act.difficulty,
                    }
                    for act in daily_acts
                ],
            )
    finally:
        db.close()


@celery_app.task
def check_streak_integrity():
    db = SessionLocal()
    try:
        users = db.query(User.id).filter(User.is_active == True).yield_per(500)

        for row in users:
            validate_streak(db, row.id)
    finally:
        db.close()


@celery_app.task
def send_morning_reminder():
    db = SessionLocal()
    try:
        adhkar_count = db.query(func.count(Adhkar.id)).filter(Adhkar.time_of_day == TimeOfDay.morning).scalar() or 0

        if adhkar_count > 0:
            offset = random.randint(0, adhkar_count - 1)
            featured = (
                db.query(Adhkar)
                .filter(Adhkar.time_of_day == TimeOfDay.morning)
                .offset(offset)
                .limit(1)
                .first()
            )
            message = f"Morning dhikr: {featured.text_translation[:120]}..."
        else:
            message = "Start your day with a good deed."

        for row in db.query(User.id).filter(User.is_active == True).all():
            create_notification(
                db,
                row.id,
                title="Morning reminder",
                message=message,
            )
    finally:
        db.close()


@celery_app.task
def aggregate_weekly_stats():
    db = SessionLocal()
    compute_weekly_stats(db)
    db.close()


@celery_app.task
def jar_completion_celebration(user_id: int):
    db = SessionLocal()
    try:
        create_notification(
            db,
            user_id,
            title="Jar complete",
            message="Your Sadaqah Jar is Complete!",
        )
    finally:
        db.close()


@celery_app.task
def family_jar_completion_celebration(jar_id: int):
    db = SessionLocal()
    try:
        member_ids = [
            row.user_id
            for row in db.query(FamilyJarMember.user_id)
            .filter(FamilyJarMember.family_jar_id == jar_id)
            .all()
        ]
        if not member_ids:
            return
        for uid in member_ids:
            create_notification(
                db,
                uid,
                title="Family jar complete",
                message="Your family jar is full! Great teamwork!",
            )
    finally:
        db.close()


_FRIDAY_RECOMMENDATIONS_PUSH = [
    "Send abundant salawat upon the Prophet today.",
    "Read Surah Al-Kahf - it is a light between two Fridays.",
    "Give charity today - Friday charity is specially multiplied.",
    "Make dua in the last hour after Asr - it is the hour of acceptance.",
    "Reach out to a relative to strengthen family ties.",
]

_LAST_TEN_RECOMMENDATIONS = [
    "Last 10 nights: Wake up for Qiyam al-Layl and pour your heart out to Allah.",
    "Last 10 nights: Increase your dhikr - SubhanAllah, Alhamdulillah, Allahu Akbar.",
    "Last 10 nights: Make sincere dua - this is the night of decree. Ask abundantly.",
    "Last 10 nights: Recite and reflect on Quran - every letter is multiplied.",
    "Last 10 nights: Give charity secretly - it extinguishes sins and pleases Allah.",
]


@celery_app.task
def send_friday_reminder():
    db = SessionLocal()
    try:
        day_index = datetime.utcnow().isocalendar()[1] * 7 + datetime.utcnow().weekday()
        message = _FRIDAY_RECOMMENDATIONS_PUSH[day_index % len(_FRIDAY_RECOMMENDATIONS_PUSH)]

        for row in db.query(User.id).filter(User.friday_reminder == True).all():
            create_notification(
                db,
                row.id,
                title="Friday reminder",
                message=message,
            )
    finally:
        db.close()


@celery_app.task
def send_last_ten_nights_reminder():
    """Fires only on the last 10 nights of Ramadan.

    The scheduled crontab should run once per night during the last 10 days;
    the task itself also guards with is_last_10_nights() so even a misconfigured
    schedule won't fire outside the window.
    """
    from app.services.hijri_service import is_last_10_nights

    if not is_last_10_nights():
        return

    db = SessionLocal()
    try:
        day_index = datetime.utcnow().timetuple().tm_yday
        message = _LAST_TEN_RECOMMENDATIONS[day_index % len(_LAST_TEN_RECOMMENDATIONS)]

        for row in db.query(User.id).filter(User.is_active == True).all():
            create_notification(
                db,
                row.id,
                title="Last 10 nights reminder",
                message=message,
            )
    finally:
        db.close()
