import hashlib
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.cache import cache_daily_acts
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.models.sadaqah_log import SadaqahLog
from app.journey.models import JourneyAdhkarProgress, JourneyQuranProgress
from app.journey.models import JourneyPrayerCompletion
from app.models.adhkar import Adhkar, TimeOfDay
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


_PENDING_SCHEDULE_STATUSES = {"scheduled", "queued"}


def _cancel_pending_schedule(schedule: ScheduledNotification) -> None:
    """Cancel pending work without rewriting delivered reminder history."""
    if schedule.status in _PENDING_SCHEDULE_STATUSES:
        schedule.status = "cancelled"


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
            _schedule_reminders_for_user(db, user)
    finally:
        db.close()


@celery_app.task
def schedule_user_aware_reminders(user_id: int):
    """Refresh one user's current-day schedule after preference changes.

    Beat rebuilds every user at 00:05 UTC. This task closes the gap for a
    person who enables reminders later in the day, without making the API
    request wait for prayer-time lookup or reminder persistence.
    """
    db = SessionLocal()
    try:
        _apply_rhythm_deep_links(db)
        user = (
            db.query(User)
            .filter(User.id == user_id, User.deleted_at.is_(None))
            .first()
        )
        if user is not None:
            _schedule_reminders_for_user(db, user, future_only=True)
    finally:
        db.close()


def _schedule_reminders_for_user(
    db, user: User, *, future_only: bool = False
) -> None:
    timezone_name = user.preferences.timezone if user.preferences else None
    timezone_name = _valid_timezone_name(timezone_name)
    try:
        local_date = datetime.now(ZoneInfo(timezone_name)).date()
        # Location is only required for prayer-relative reminders. We can
        # still give the user the time-aware daily rhythm using their saved
        # timezone, so a missing location does not make reminders a no-op.
        if user.latitude is None or user.longitude is None:
            _cancel_prayer_relative_schedules(
                db=db,
                user_id=user.id,
                local_date=local_date,
            )
            logger.warning(
                "Skipping Salah/Nawafil reminders for user %s: no saved location; "
                "grant location access or set a manual location",
                user.id,
            )
            db.commit()
            _schedule_timezone_fallbacks(
                db=db,
                user=user,
                local_date=local_date,
                timezone_name=timezone_name,
                future_only=future_only,
            )
            return
        times = get_prayer_times(
            user.latitude, user.longitude, local_date, timezone_name
        )
        schedules = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=times,
            reminder_preferences=_preference_document(user, "reminder_preferences"),
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
        _apply_custom_reminder_times(
            db,
            schedules,
            user=user,
            local_date=local_date,
            timezone_name=timezone_name,
        )
        filtered = _filter_schedules_for_user(
            db, user, schedules, local_date=local_date
        )
        if future_only:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            filtered = [
                schedule
                for schedule in filtered
                if schedule.scheduled_for > now_utc
            ]
        prayer_keys = []
        for schedule in filtered:
            template = db.get(NotificationTemplate, schedule.template_id)
            if template is not None and _reminder_category(template) in {
                "prayer_fardh",
                "prayer_nafl",
            }:
                prayer_keys.append(template.key)
        logger.info(
            "Prayer reminder schedule refreshed for user %s: %d candidates, %d "
            "deliveries (%s), local date %s",
            user.id,
            len(schedules),
            len(filtered),
            ", ".join(prayer_keys) or "no prayer reminders",
            local_date,
        )
        db.commit()
        for schedule in filtered:
            if schedule.celery_task_id:
                celery_app.control.revoke(schedule.celery_task_id, terminate=False)
            result = deliver_scheduled_notification.apply_async(
                args=[schedule.id],
                eta=schedule.scheduled_for.replace(tzinfo=timezone.utc),
            )
            schedule.celery_task_id = result.id
        if filtered:
            db.commit()
    except (PrayerTimeLookupError, ValueError, KeyError, TypeError) as exc:
        db.rollback()
        try:
            # Aladhan being unavailable should degrade to timezone anchors,
            # not discard every reminder except charity.
            _schedule_timezone_fallbacks(
                db=db,
                user=user,
                local_date=local_date,
                timezone_name=timezone_name,
                future_only=future_only,
            )
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


def _cancel_prayer_relative_schedules(*, db, user_id: int, local_date) -> None:
    """Prevent stale location-based prayer ETAs from surviving a location loss."""
    rows = (
        db.query(ScheduledNotification)
        .join(NotificationTemplate, NotificationTemplate.id == ScheduledNotification.template_id)
        .filter(
            ScheduledNotification.user_id == user_id,
            ScheduledNotification.local_date == local_date.isoformat(),
            ScheduledNotification.status.in_(_PENDING_SCHEDULE_STATUSES),
        )
        .all()
    )
    for row in rows:
        template = db.get(NotificationTemplate, row.template_id)
        if template is not None and _reminder_category(template) in {
            "prayer_fardh",
            "prayer_nafl",
        }:
            _cancel_pending_schedule(row)


def _enqueue_filtered_schedules(db, schedules, user_id: int) -> None:
    """Persist and enqueue already-filtered fallback schedules."""
    if not schedules:
        return
    db.add_all(schedules)
    db.commit()
    for schedule in schedules:
        if schedule.celery_task_id:
            celery_app.control.revoke(schedule.celery_task_id, terminate=False)
        result = deliver_scheduled_notification.apply_async(
            args=[schedule.id],
            eta=schedule.scheduled_for.replace(tzinfo=timezone.utc),
        )
        schedule.celery_task_id = result.id
    db.commit()


def _schedule_timezone_fallbacks(
    *, db, user: User, local_date, timezone_name: str, future_only: bool = False
) -> None:
    """Queue the useful non-prayer rhythm when exact prayer times are absent.

    A user can have a valid reminder schedule without granting location. The
    timezone anchors are deliberately conservative (morning, afternoon,
    evening, Friday and explicitly enabled Tahajjud) and use the same
    preference/completion rules as the prayer-relative path.
    """
    schedules = _schedule_timezone_rhythm(
        db=db,
        user_id=user.id,
        local_date=local_date,
        timezone_name=timezone_name,
    )
    fallback = _schedule_fallback_sadaqah(
        db=db,
        user_id=user.id,
        local_date=local_date,
        timezone_name=timezone_name,
    )
    if fallback is not None:
        schedules.append(fallback)

    filtered = _filter_schedules_for_user(
        db, user, schedules, local_date=local_date
    )
    if future_only:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        filtered = [
            schedule
            for schedule in filtered
            if schedule.scheduled_for > now_utc
        ]
    _enqueue_filtered_schedules(db, filtered, user.id)


def _filter_schedules_for_user(
    db, user: User, schedules, *, local_date
) -> list[ScheduledNotification]:
    """Apply category, opt-in, completion and frequency rules consistently."""
    frequency = get_frequency(db, user.id)
    core_categories = {
        "prayer_fardh",
        "adhkar_morning",
        "adhkar_evening",
        "quran",
    }
    category_priority = {
        "prayer_fardh": 0,
        "adhkar_morning": 1,
        "adhkar_evening": 1,
        "quran": 2,
        "prayer_nafl": 3,
    }
    max_per_category = {
        "prayer_fardh": 5,
        "prayer_nafl": 2,
        "adhkar_morning": 1,
        "adhkar_evening": 1,
        "quran": 1,
    }
    daily_limit = {"low": 8, "medium": 10, "high": 12}.get(frequency, 10)
    nawafil_after_salah_enabled = _explicit_reminder_enabled(
        user, "nawafil_after_salah", default=False
    )
    if nawafil_after_salah_enabled:
        # The opt-in explicitly requests all three prayer-relative reminders;
        # leave room for them without raising unrelated Nafl traffic.
        max_per_category["prayer_nafl"] = 5
        daily_limit += 3
    candidates = []
    for schedule in schedules:
        template = db.get(NotificationTemplate, schedule.template_id)
        if template is None:
            continue
        category = _reminder_category(template)
        if _should_skip_for_user(db, user, template, local_date=local_date):
            # Prayer-relative schedules are already in the session. Preserve
            # the existing audit trail for those rows; unsaved fallback rows
            # are simply omitted below.
            if schedule in db:
                _cancel_pending_schedule(schedule)
            continue
        if not is_category_enabled(db, user.id, category):
            if schedule in db:
                _cancel_pending_schedule(schedule)
            continue
        is_opted_in_post_salah_nawafil = (
            nawafil_after_salah_enabled
            and template.key
            in {
                "nawafil_after_dhuhr",
                "nawafil_after_maghrib",
                "nawafil_after_isha",
            }
        )
        if (
            frequency == "low"
            and category not in core_categories
            and not is_opted_in_post_salah_nawafil
        ):
            if schedule in db:
                _cancel_pending_schedule(schedule)
            continue
        candidates.append((category_priority.get(category, 4), schedule, category))

    candidates.sort(key=lambda item: (item[0], item[1].scheduled_for))
    category_counts: dict[str, int] = {}
    filtered = []
    for _, schedule, category in candidates:
        limit = max_per_category.get(category, 1)
        if category_counts.get(category, 0) >= limit or len(filtered) >= daily_limit:
            if schedule in db:
                _cancel_pending_schedule(schedule)
            continue
        category_counts[category] = category_counts.get(category, 0) + 1
        filtered.append(schedule)
    return filtered


def _valid_timezone_name(value: str | None) -> str:
    """Use UTC when a user has not selected a timezone yet."""
    if value:
        try:
            ZoneInfo(value)
            return value
        except Exception:
            logger.warning("Invalid user timezone %r; using UTC", value)
    return "UTC"


def _preference_document(user: User, field: str) -> dict:
    raw = getattr(user.preferences, field, "{}") if user.preferences else "{}"
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


_SALAH_TEMPLATE_NAMES = {
    "fajr_reminder": "fajr",
    "pre_fajr": "fajr",
    "dhuhr_reminder": "dhuhr",
    "pre_dhuhr": "dhuhr",
    "asr_reminder": "asr",
    "maghrib_reminder": "maghrib",
    "pre_maghrib": "maghrib",
    "isha_reminder": "isha",
    "pre_isha": "isha",
}

_REMINDER_CATEGORY_OVERRIDES = {
    "morning_adhkar": "adhkar_morning",
    "morning_adhkar_expanded": "adhkar_morning",
    "evening_adhkar": "adhkar_evening",
    "evening_adhkar_expanded": "adhkar_evening",
    "quran_reminder": "quran",
    "quran_verse": "quran",
    "salatul_duha": "prayer_nafl",
    "duha_reminder": "prayer_nafl",
    "witr_reminder": "prayer_nafl",
    "witr_reminder_expanded": "prayer_nafl",
    "nawafil_after_dhuhr": "prayer_nafl",
    "nawafil_after_maghrib": "prayer_nafl",
    "nawafil_after_isha": "prayer_nafl",
    **{key: "prayer_fardh" for key in _SALAH_TEMPLATE_NAMES},
}


def _reminder_category(template: NotificationTemplate) -> str:
    return _REMINDER_CATEGORY_OVERRIDES.get(template.key, template.category)


def _prayer_reminder_enabled(user: User, prayer_name: str) -> bool:
    prefs = _preference_document(user, "reminder_preferences")
    reminders = prefs.get("prayer_reminders", {})
    value = reminders.get(prayer_name, {}) if isinstance(reminders, dict) else {}
    if isinstance(value, bool):
        return value
    return value.get("enabled", True) if isinstance(value, dict) else True


def _custom_reminder_time(user: User, key: str) -> time | None:
    prefs = _preference_document(user, "reminder_preferences")
    values = prefs.get("daily_times", {})
    raw = values.get(key) if isinstance(values, dict) else None
    if not isinstance(raw, str):
        return None
    try:
        return time.fromisoformat(raw)
    except ValueError:
        logger.warning("Ignoring invalid custom reminder time for %s", key)
        return None


def _apply_custom_reminder_times(
    db, schedules, *, user: User, local_date, timezone_name: str
) -> None:
    zone = ZoneInfo(timezone_name)
    keys = {
        "morning_adhkar": "morning_adhkar",
        "morning_adhkar_expanded": "morning_adhkar",
        "evening_adhkar": "evening_adhkar",
        "evening_adhkar_expanded": "evening_adhkar",
        "quran_reminder": "quran",
        "quran_verse": "quran",
    }
    for schedule in schedules:
        template = db.get(NotificationTemplate, schedule.template_id)
        if template is None:
            continue
        setting_key = keys.get(template.key)
        if setting_key is None:
            continue
        setting = _custom_reminder_time(user, setting_key)
        if setting is not None:
            schedule.scheduled_for = datetime.combine(
                local_date, setting, tzinfo=zone
            ).astimezone(timezone.utc).replace(tzinfo=None)


def _explicit_reminder_enabled(user: User, key: str, *, default: bool) -> bool:
    reminders = _preference_document(user, "reminder_preferences")
    value = reminders.get(key)
    if value is None:
        value = reminders.get(f"{key}_enabled")
    return default if value is None else bool(value)


def _is_friday_enabled(user: User) -> bool:
    notifications = _preference_document(user, "notification_preferences")
    if "friday_reminder" in notifications:
        return bool(notifications["friday_reminder"])
    reminders = _preference_document(user, "reminder_preferences")
    if "friday_reminder" in reminders:
        return bool(reminders["friday_reminder"])
    return bool(reminders.get("friday", False))


def _has_local_activity(db, user_id: int, local_date, *, kind: str, timezone_name: str) -> bool:
    zone = ZoneInfo(timezone_name)
    start = datetime.combine(local_date, time.min, tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
    end = datetime.combine(local_date + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
    if kind == "quran":
        return db.query(JourneyQuranProgress.id).filter(
            JourneyQuranProgress.user_id == user_id,
            JourneyQuranProgress.last_read_at >= start,
            JourneyQuranProgress.last_read_at < end,
        ).first() is not None
    if kind in {"adhkar", "adhkar_morning", "adhkar_evening"}:
        query = db.query(JourneyAdhkarProgress.id).join(
            Adhkar, Adhkar.id == JourneyAdhkarProgress.adhkar_id
        ).filter(
            JourneyAdhkarProgress.user_id == user_id,
            JourneyAdhkarProgress.updated_at >= start,
            JourneyAdhkarProgress.updated_at < end,
            JourneyAdhkarProgress.count > 0,
        )
        if kind == "adhkar_morning":
            query = query.filter(Adhkar.time_of_day == TimeOfDay.morning)
        elif kind == "adhkar_evening":
            query = query.filter(Adhkar.time_of_day == TimeOfDay.evening)
        return query.first() is not None
    if kind == "charity":
        return db.query(SadaqahLog.id).filter(
            SadaqahLog.user_id == user_id,
            SadaqahLog.date == local_date,
        ).first() is not None
    return False


def _has_prayer_completion(db, user_id: int, local_date, prayer_name: str) -> bool:
    return db.query(JourneyPrayerCompletion.id).filter(
        JourneyPrayerCompletion.user_id == user_id,
        JourneyPrayerCompletion.local_date == local_date,
        JourneyPrayerCompletion.prayer_name == prayer_name,
    ).first() is not None


def _should_skip_for_user(db, user: User, template: NotificationTemplate, *, local_date) -> bool:
    if template.key.startswith("friday") or template.key == "friday_expanded":
        if not _is_friday_enabled(user):
            return True
    if template.key == "tahajjud_reminder" and not _explicit_reminder_enabled(
        user, "tahajjud", default=False
    ):
        return True
    if template.key in {
        "nawafil_after_dhuhr",
        "nawafil_after_maghrib",
        "nawafil_after_isha",
    } and not _explicit_reminder_enabled(
        user, "nawafil_after_salah", default=False
    ):
        return True
    prayer_name = _SALAH_TEMPLATE_NAMES.get(template.key)
    if prayer_name and (
        not _prayer_reminder_enabled(user, prayer_name)
        or _has_prayer_completion(db, user.id, local_date, prayer_name)
    ):
        return True
    timezone_name = _valid_timezone_name(user.preferences.timezone if user.preferences else None)
    category = _reminder_category(template)
    if category in {"quran", "reading"} and _has_local_activity(
        db, user.id, local_date, kind="quran", timezone_name=timezone_name
    ):
        return True
    adhkar_kind = (
        category if category in {"adhkar_morning", "adhkar_evening"} else
        "adhkar" if category == "adhkar" else None
    )
    if adhkar_kind and _has_local_activity(
        db, user.id, local_date, kind=adhkar_kind, timezone_name=timezone_name
    ):
        return True
    return category == "charity" and _has_local_activity(
        db, user.id, local_date, kind="charity", timezone_name=timezone_name
    )


def _schedule_timezone_rhythm(*, db, user_id: int, local_date, timezone_name: str):
    """Schedule non-prayer rhythm anchors when exact prayer times are unavailable."""
    zone = ZoneInfo(_valid_timezone_name(timezone_name))
    user = db.get(User, user_id)
    if user is None:
        return []
    slots = [
        ("morning_adhkar", _custom_reminder_time(user, "morning_adhkar") or time(8, 0)),
        ("quran_reminder", _custom_reminder_time(user, "quran") or time(14, 0)),
        ("evening_adhkar", _custom_reminder_time(user, "evening_adhkar") or time(18, 30)),
    ]
    # Keep one reflective pause, but vary its time predictably by user/day so
    # the same person does not receive it at exactly the same minute every day.
    # The stable digest also makes retries idempotent and keeps the rhythm calm.
    digest = hashlib.sha256(f"reflection:{user_id}:{local_date}".encode()).hexdigest()
    reflection_minutes = 19 * 60 + int(digest[:8], 16) % 120
    slots.append(
        (
            "reflection_prompt",
            time(reflection_minutes // 60, reflection_minutes % 60),
        )
    )
    if local_date.weekday() == 4 and _is_friday_enabled(user):
        slots.extend((("friday_reminder", time(9, 0)), ("friday_kahf_reminder", time(15, 0))))
    if _explicit_reminder_enabled(user, "tahajjud", default=False):
        slots.append(("tahajjud_reminder", time(22, 0)))
    schedules = []
    for key, local_time in slots:
        template = db.query(NotificationTemplate).filter(
            NotificationTemplate.key == key,
            NotificationTemplate.enabled.is_(True),
        ).first()
        if template is None or _should_skip_for_user(db, user, template, local_date=local_date):
            continue
        if not is_category_enabled(db, user_id, _reminder_category(template)):
            continue
        scheduled_for = datetime.combine(local_date, local_time, tzinfo=zone).astimezone(
            timezone.utc
        ).replace(tzinfo=None)
        existing = db.query(ScheduledNotification).filter_by(
            user_id=user_id, template_id=template.id, local_date=local_date.isoformat()
        ).first()
        if existing is not None:
            if existing.status == "cancelled":
                existing.status = "scheduled"
                existing.scheduled_for = scheduled_for
                schedules.append(existing)
            continue
        schedules.append(ScheduledNotification(
            user_id=user_id,
            template_id=template.id,
            local_date=local_date.isoformat(),
            scheduled_for=scheduled_for,
        ))
    return schedules


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
        "nawafil_after_dhuhr": "/home",
        "nawafil_after_maghrib": "/home",
        "nawafil_after_isha": "/home",
        "reflection_prompt": "/journey?tab=reflection",
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
        "prayer_fardh": "prayer_request",
        "prayer_nafl": "prayer_request",
        "adhkar": "adhkar",
        "adhkar_morning": "adhkar",
        "adhkar_evening": "adhkar",
        "reading": "reading_progress",
        "quran": "reading_progress",
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
        user = db.get(User, schedule.user_id)
        if user is None:
            schedule.status = "cancelled"
            db.commit()
            return
        try:
            schedule_date = date.fromisoformat(schedule.local_date)
        except (TypeError, ValueError):
            schedule.status = "cancelled"
            db.commit()
            return
        # Re-check preferences and completion at delivery time. A reminder
        # queued before a user changed settings must never bypass that choice.
        category = _reminder_category(template)
        if not is_category_enabled(db, schedule.user_id, category) or _should_skip_for_user(
            db, user, template, local_date=schedule_date
        ):
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
            category=category,
            idempotency_key=idempotency_key,
        )
        notification_type = _map_category_to_notification_type(category)
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
                "category": category,
                "template_key": template.key,
                "deep_link": deep_link or f"/notifications/{notification.id}",
                "notification_id": str(notification.id),
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
