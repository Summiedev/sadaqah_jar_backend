from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.cache import cache_daily_acts
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.notifications.models import NotificationTemplate, ScheduledNotification
from app.services.analytics_service import compute_weekly_stats
from app.services.notification_service import create_notification
from app.services.personalization_service import generate_personalized_acts
from app.services.push_notification_service import send_push_notification
from app.services.prayer_reminder_service import schedule_prayer_relative_templates
from app.services.prayer_time_service import PrayerTimeLookupError, get_prayer_times
from app.services.reminder_content_service import resolve_reminder_content
from app.services.ramadan_service import is_ramadan
from app.services.streak_service import validate_streak


@celery_app.task
def generate_daily_acts():
    db = SessionLocal()
    try:
        candidate_query = db.query(SadaqahAct).filter(SadaqahAct.verified)
        if not is_ramadan():
            candidate_query = candidate_query.filter(not SadaqahAct.is_ramadan_only)

        candidate_acts = candidate_query.all()

        active_user_ids = [
            row[0] for row in db.query(User.id).filter(User.deleted_at.is_(None)).all()
        ]

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
def schedule_daily_prayer_reminders():
    """Calculate and enqueue today's prayer-relative reminders per user.

    The durable schedule table makes this task safe to retry and gives later
    delivery stages an audit trail instead of relying solely on broker ETA.
    """
    db = SessionLocal()
    try:
        users = (
            db.query(User)
            .filter(
                User.deleted_at.is_(None),
                User.latitude.is_not(None),
                User.longitude.is_not(None),
            )
            .yield_per(250)
        )
        for user in users:
            timezone_name = user.preferences.timezone if user.preferences else None
            if not timezone_name:
                continue
            try:
                local_date = datetime.now(ZoneInfo(timezone_name)).date()
                times = get_prayer_times(
                    user.latitude, user.longitude, local_date, timezone_name
                )
                schedules = schedule_prayer_relative_templates(
                    db, user_id=user.id, local_date=local_date, prayer_times=times
                )
                db.commit()
                for schedule in schedules:
                    result = deliver_scheduled_notification.apply_async(
                        args=[schedule.id], eta=schedule.scheduled_for.replace(tzinfo=timezone.utc)
                    )
                    schedule.celery_task_id = result.id
                if schedules:
                    db.commit()
            except (PrayerTimeLookupError, ValueError):
                db.rollback()
    finally:
        db.close()


def _map_category_to_notification_type(category: str) -> str:
    mapping = {
        'charity': 'sadaqah_act',
        'reflection': 'reflection',
        'family': 'family_activity',
        'prayer': 'prayer_request',
        'adhkar': 'adhkar',
        'reading': 'reading_progress',
        'islamic_occasions': 'friday',
        'journey': 'goal_progress',
    }
    return mapping.get(category, 'general')


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def deliver_scheduled_notification(self, schedule_id: int):
    """Deliver a persisted reminder once.

    Idempotency: the schedule row's status is checked before delivery and
    the notification row carries an idempotency key derived from the
    schedule id, so retries never create duplicate notifications.
    """
    db = SessionLocal()
    try:
        schedule = db.get(ScheduledNotification, schedule_id)
        if schedule is None or schedule.status != "scheduled":
            return
        template = db.get(NotificationTemplate, schedule.template_id)
        if template is None or not template.enabled:
            schedule.status = "cancelled"
            db.commit()
            return
        title, message = resolve_reminder_content(db, schedule, template)
        idempotency_key = f"scheduled:{schedule.id}"
        create_notification(
            db,
            schedule.user_id,
            title=title,
            message=message,
            category=template.category,
            idempotency_key=idempotency_key,
        )
        notification_type = _map_category_to_notification_type(template.category)
        send_push_notification(
            db,
            user_id=schedule.user_id,
            title=title,
            body=message,
            notification_type=notification_type,
            data={"category": template.category, "template_key": template.key},
        )
        schedule.status = "delivered"
        schedule.delivered_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            self.retry(exc=exc)
        except Exception:
            db2 = SessionLocal()
            try:
                sched = db2.get(ScheduledNotification, schedule_id)
                if sched is not None and sched.status == "scheduled":
                    sched.status = "failed"
                    db2.commit()
            finally:
                db2.close()
            raise
    finally:
        db.close()


@celery_app.task
def check_streak_integrity():
    db = SessionLocal()
    try:
        users = db.query(User.id).filter(User.deleted_at.is_(None)).yield_per(500)

        for row in users:
            validate_streak(db, row.id)
    finally:
        db.close()


@celery_app.task
def send_morning_reminder():
    """Compatibility entry point; morning adhkar is prayer-relative now."""
    schedule_daily_prayer_reminders()


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
    """Legacy task - no-op. Family domain uses activity timeline instead."""
    pass


_LAST_TEN_RECOMMENDATIONS = [
    "Last 10 nights: Wake up for Qiyam al-Layl and pour your heart out to Allah.",
    "Last 10 nights: Increase your dhikr - SubhanAllah, Alhamdulillah, Allahu Akbar.",
    "Last 10 nights: Make sincere dua - this is the night of decree. Ask abundantly.",
    "Last 10 nights: Recite and reflect on Quran - every letter is multiplied.",
    "Last 10 nights: Give charity secretly - it extinguishes sins and pleases Allah.",
]


@celery_app.task
def send_friday_reminder():
    """Compatibility entry point; Friday delivery uses the shared FCM path."""
    schedule_daily_prayer_reminders()


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

        for row in db.query(User.id).filter(User.deleted_at.is_(None)).all():
            create_notification(
                db,
                row.id,
                title="Last 10 nights reminder",
                message=message,
            )
    finally:
        db.close()
