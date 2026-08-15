import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.cache import cache_daily_acts
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.notifications.models import NotificationTemplate, ScheduledNotification, SchedulingStrategy
from app.services.analytics_service import compute_weekly_stats
from app.services.notification_service import create_notification
from app.services.personalization_service import generate_personalized_acts
from app.services.push_notification_service import send_push_notification
from app.notifications.preferences import get_frequency, is_category_enabled
from app.services.prayer_reminder_service import schedule_prayer_relative_templates
from app.services.prayer_time_service import PrayerTimeLookupError, get_prayer_times
from app.services.reminder_content_service import resolve_reminder_content
from app.services.ramadan_service import is_ramadan
from app.services.streak_service import validate_streak

logger = logging.getLogger(__name__)


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
        _apply_rhythm_deep_links(db)
        users = (
            db.query(User)
            .filter(
                User.deleted_at.is_(None),
            )
            .yield_per(250)
        )
        for user in users:
            timezone_name = user.preferences.timezone if user.preferences else None
            if not timezone_name:
                continue
            try:
                local_date = datetime.now(ZoneInfo(timezone_name)).date()
                # A charity prompt is useful even when a prayer provider is
                # temporarily unavailable or location has not been granted.
                # Keep it on the user's local daytime schedule instead of
                # silently dropping every reminder for that account.
                if user.latitude is None or user.longitude is None:
                    fallback = _schedule_fallback_sadaqah(
                        db, user_id=user.id, local_date=local_date, timezone_name=timezone_name
                    )
                    _enqueue_filtered_schedules(db, [fallback] if fallback else [], user.id)
                    continue
                times = get_prayer_times(
                    user.latitude, user.longitude, local_date, timezone_name
                )
                schedules = schedule_prayer_relative_templates(
                    db, user_id=user.id, local_date=local_date, prayer_times=times
                )
                random_sadaqah = _schedule_random_sadaqah(
                    db,
                    user_id=user.id,
                    local_date=local_date,
                    prayer_times=times,
                )
                if random_sadaqah is not None:
                    db.add(random_sadaqah)
                    schedules.append(random_sadaqah)
                # Filter schedules by category preference and frequency
                frequency = get_frequency(db, user.id)
                filtered = []
                for schedule in schedules:
                    template = db.get(NotificationTemplate, schedule.template_id)
                    if template is None:
                        continue
                    if not is_category_enabled(db, user.id, template.category):
                        continue
                    # Frequency control: low = skip ~50% of non-essential reminders
                    if frequency == "low" and template.category not in {
                        "prayer_fardh",
                        "prayer",
                        "adhkar_morning",
                        "adhkar_evening",
                    }:
                        import random

                        if random.random() < 0.5:
                            continue
                    filtered.append(schedule)
                db.commit()
                for schedule in filtered:
                    result = deliver_scheduled_notification.apply_async(
                        args=[schedule.id],
                        eta=schedule.scheduled_for.replace(tzinfo=timezone.utc),
                    )
                    schedule.celery_task_id = result.id
                if filtered:
                    db.commit()
            except (PrayerTimeLookupError, ValueError) as exc:
                db.rollback()
                try:
                    fallback = _schedule_fallback_sadaqah(
                        db, user_id=user.id, local_date=local_date, timezone_name=timezone_name
                    )
                    if fallback is not None:
                        db.add(fallback)
                        db.commit()
                        result = deliver_scheduled_notification.apply_async(
                            args=[fallback.id],
                            eta=fallback.scheduled_for.replace(tzinfo=timezone.utc),
                        )
                        fallback.celery_task_id = result.id
                        db.commit()
                except Exception:
                    db.rollback()
                logger.warning(
                    "Could not schedule aware reminders for user %s: %s",
                    user.id,
                    exc,
                )
            except Exception:
                db.rollback()
                logger.exception(
                    "Unexpected error while scheduling aware reminders for user %s",
                    user.id,
                )
    finally:
        db.close()


def _enqueue_filtered_schedules(db, schedules, user_id: int) -> None:
    """Persist and enqueue already-filtered fallback schedules."""
    if not schedules:
        return
    db.add_all(schedules)
    db.commit()
    for schedule in schedules:
        result = deliver_scheduled_notification.apply_async(
            args=[schedule.id],
            eta=schedule.scheduled_for.replace(tzinfo=timezone.utc),
        )
        schedule.celery_task_id = result.id
    db.commit()


def _schedule_random_sadaqah(*, db, user_id: int, local_date, prayer_times):
    """Add at most one gentle sadaqah prompt in a safe daytime window.

    The date and user ID produce a stable daily position, so retries never
    move an already-scheduled reminder or create a second one. Some days are
    intentionally skipped to keep the prompt occasional rather than noisy.
    """
    if not is_category_enabled(db, user_id, "charity"):
        return None
    frequency = get_frequency(db, user_id)
    digest = hashlib.sha256(f"{user_id}:{local_date}".encode()).hexdigest()
    if int(digest[:2], 16) % (3 if frequency == "high" else 4) == 0:
        return None

    template = (
        db.query(NotificationTemplate)
        .filter(NotificationTemplate.key == "random_sadaqah_prompt")
        .first()
    )
    if template is None:
        template = NotificationTemplate(
            key="random_sadaqah_prompt",
            title_template="A small sadaqah",
            message_template="{title}. {message}",
            category="charity",
            strategy=SchedulingStrategy.RANDOMIZED.value,
            strategy_config=json.dumps(
                {
                    "content_source": "good_deeds",
                    "deep_link": "/home?open=sadaqah",
                }
            ),
            enabled=True,
        )
        db.add(template)
        db.flush()

    existing = (
        db.query(ScheduledNotification)
        .filter_by(
            user_id=user_id,
            template_id=template.id,
            local_date=local_date.isoformat(),
        )
        .first()
    )
    if existing is not None:
        return None

    start = prayer_times.duha_start + timedelta(minutes=45)
    end = prayer_times.asr - timedelta(minutes=45)
    if end <= start:
        return None
    window_minutes = int((end - start).total_seconds() // 60)
    offset = int(digest[2:10], 16) % max(window_minutes, 1)
    return ScheduledNotification(
        user_id=user_id,
        template_id=template.id,
        local_date=local_date.isoformat(),
        scheduled_for=(start + timedelta(minutes=offset))
        .astimezone(timezone.utc)
        .replace(tzinfo=None),
    )


def _schedule_fallback_sadaqah(*, db, user_id: int, local_date, timezone_name: str):
    """Schedule the same occasional prompt without prayer-time dependency."""
    local_zone = ZoneInfo(timezone_name)
    digest = hashlib.sha256(f"fallback:{user_id}:{local_date}".encode()).hexdigest()
    # Keep the reminder in a quiet daytime window and vary it per user/day.
    start = datetime.combine(local_date, datetime.min.time(), tzinfo=local_zone).replace(
        hour=13, minute=0
    )
    offset = int(digest[:8], 16) % (3 * 60)
    template = (
        db.query(NotificationTemplate)
        .filter(NotificationTemplate.key == "random_sadaqah_prompt")
        .first()
    )
    if template is None:
        template = NotificationTemplate(
            key="random_sadaqah_prompt",
            title_template="A small sadaqah",
            message_template="{title}. {message}",
            category="charity",
            strategy=SchedulingStrategy.RANDOMIZED.value,
            strategy_config=json.dumps(
                {"content_source": "good_deeds", "deep_link": "/home?open=sadaqah"}
            ),
            enabled=True,
        )
        db.add(template)
        db.flush()
    if not is_category_enabled(db, user_id, "charity"):
        return None
    if (
        db.query(ScheduledNotification)
        .filter_by(
            user_id=user_id,
            template_id=template.id,
            local_date=local_date.isoformat(),
        )
        .first()
        is not None
    ):
        return None
    return ScheduledNotification(
        user_id=user_id,
        template_id=template.id,
        local_date=local_date.isoformat(),
        scheduled_for=(start + timedelta(minutes=offset))
        .astimezone(timezone.utc)
        .replace(tzinfo=None),
    )


def _apply_rhythm_deep_links(db) -> None:
    """Keep existing seeded templates aligned after a deployment."""
    links = {
        "morning_adhkar": "/journey/adhkar/morning",
        "morning_adhkar_expanded": "/journey/adhkar/morning",
        "evening_adhkar": "/journey/adhkar/evening",
        "evening_adhkar_expanded": "/journey/adhkar/evening",
        "quran_reminder": "/journey?tab=quran",
        "quran_verse": "/journey?tab=quran",
        "friday_kahf_reminder": "/journey?tab=quran&surah=18",
        "friday_reminder": "/journey",
        "friday_expanded": "/journey",
        "tahajjud_reminder": "/home",
        "random_sadaqah_prompt": "/home?open=sadaqah",
    }
    changed = False
    templates = (
        db.query(NotificationTemplate)
        .filter(NotificationTemplate.key.in_(links))
        .all()
    )
    for template in templates:
        try:
            config = json.loads(template.strategy_config or "{}")
        except (TypeError, json.JSONDecodeError):
            config = {}
        if config.get("deep_link") == links[template.key]:
            continue
        config["deep_link"] = links[template.key]
        template.strategy_config = json.dumps(config)
        changed = True
    if changed:
        db.flush()


def _map_category_to_notification_type(category: str) -> str:
    mapping = {
        "charity": "sadaqah_act",
        "reflection": "reflection",
        "family": "family_activity",
        "prayer": "prayer_request",
        "adhkar": "adhkar",
        "reading": "reading_progress",
        "islamic_occasions": "friday",
        "journey": "goal_progress",
    }
    return mapping.get(category, "general")


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
        notification = create_notification(
            db,
            schedule.user_id,
            title=title,
            message=message,
            category=template.category,
            idempotency_key=idempotency_key,
        )
        notification_type = _map_category_to_notification_type(template.category)
        template_config = {}
        try:
            template_config = json.loads(template.strategy_config or "{}")
        except (TypeError, json.JSONDecodeError):
            template_config = {}
        deep_link = template_config.get("deep_link")
        delivered = send_push_notification(
            db,
            user_id=schedule.user_id,
            title=title,
            body=message,
            notification_type=notification_type,
            data={
                "category": template.category,
                "template_key": template.key,
                "deep_link": deep_link or f"/notifications/{notification.id}",
            },
        )
        if delivered:
            schedule.status = "delivered"
            schedule.delivered_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            # Keep the in-app notification, but make the failed push visible to
            # operators instead of falsely reporting successful delivery.
            schedule.status = "failed"
            logger.warning(
                "Reminder %s created in-app but reached no FCM device for user %s",
                schedule.id,
                schedule.user_id,
            )
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
