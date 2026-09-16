"""Build durable, prayer-relative reminder schedules from notification templates."""

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.notifications.models import ScheduledNotification, SchedulingStrategy
from app.services.prayer_time_service import PrayerTimes


# Several seeded templates intentionally describe the same moment in the
# daily rhythm. Keep one canonical reminder per group so a retry or a seed
# update cannot make the user receive duplicate prompts.
_TEMPLATE_GROUPS = {
    "fajr_reminder": ("salah_fajr", 0),
    "pre_fajr": ("salah_fajr", 1),
    "dhuhr_reminder": ("salah_dhuhr", 0),
    "pre_dhuhr": ("salah_dhuhr", 1),
    "asr_reminder": ("salah_asr", 0),
    "maghrib_reminder": ("salah_maghrib", 0),
    "pre_maghrib": ("salah_maghrib", 1),
    "isha_reminder": ("salah_isha", 0),
    "pre_isha": ("salah_isha", 1),
    "morning_adhkar": ("morning_adhkar", 0),
    "morning_adhkar_expanded": ("morning_adhkar", 1),
    "evening_adhkar": ("evening_adhkar", 0),
    "evening_adhkar_expanded": ("evening_adhkar", 1),
    "quran_reminder": ("quran", 0),
    "quran_verse": ("quran", 1),
    "friday_reminder": ("friday", 0),
    "friday_expanded": ("friday", 1),
    "witr_reminder": ("witr", 0),
    "witr_reminder_expanded": ("witr", 1),
    "salatul_duha": ("duha", 0),
    "duha_reminder": ("duha", 1),
    "nawafil_after_dhuhr": ("nawafil_after_dhuhr", 0),
    "nawafil_after_maghrib": ("nawafil_after_maghrib", 0),
    "nawafil_after_isha": ("nawafil_after_isha", 0),
}

_SALAH_TEMPLATE_PRAYERS = {
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


def _config(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def schedule_prayer_relative_templates(
    db: Session,
    *,
    user_id: int,
    local_date: date,
    prayer_times: PrayerTimes,
    reminder_preferences: dict | None = None,
) -> list[ScheduledNotification]:
    """Persist one schedule per user/template/day, returning new rows only.

    Template config contract: ``{"anchor": "fajr", "offset_minutes": -10}``.
    Valid anchors are the fields returned by ``PrayerTimes`` including
    ``duha_start`` and ``duha_end``.
    """
    from app.notifications.models import NotificationTemplate

    templates = (
        db.query(NotificationTemplate)
        .filter(
            NotificationTemplate.enabled.is_(True),
            NotificationTemplate.strategy == SchedulingStrategy.PRAYER_RELATIVE.value,
        )
        .all()
    )
    scheduled: list[ScheduledNotification] = []
    groups_seen: set[str] = set()
    templates = sorted(
        templates,
        key=lambda template: _TEMPLATE_GROUPS.get(template.key, (template.key, 99)),
    )
    for template in templates:
        existing = (
            db.query(ScheduledNotification)
            .filter_by(
                user_id=user_id,
                template_id=template.id,
                local_date=local_date.isoformat(),
            )
            .first()
        )

        def cancel_existing() -> None:
            # Preserve delivered/failed rows as audit history. Only a pending
            # schedule is changed by reconciliation.
            if existing is not None and existing.status in {"scheduled", "queued"}:
                existing.status = "cancelled"

        if template.key in {
            "nawafil_after_dhuhr",
            "nawafil_after_maghrib",
            "nawafil_after_isha",
        } and not bool((reminder_preferences or {}).get("nawafil_after_salah", False)):
            cancel_existing()
            continue
        group = _TEMPLATE_GROUPS.get(template.key)
        if group is not None and group[0] in groups_seen:
            cancel_existing()
            continue
        config = _config(template.strategy_config)
        allowed_days = config.get("days_of_week")
        if allowed_days is not None and local_date.weekday() not in allowed_days:
            cancel_existing()
            continue
        anchor = config.get("anchor")
        if not isinstance(anchor, str):
            cancel_existing()
            continue
        try:
            offset = int(config.get("offset_minutes", 0))
            prayer_name = _SALAH_TEMPLATE_PRAYERS.get(template.key)
            prayer_settings = (reminder_preferences or {}).get("prayer_reminders", {})
            prayer_setting = (
                prayer_settings.get(prayer_name, {})
                if isinstance(prayer_settings, dict) and prayer_name
                else {}
            )
            if isinstance(prayer_setting, bool):
                if not prayer_setting:
                    cancel_existing()
                    continue
            elif isinstance(prayer_setting, dict):
                if prayer_setting.get("enabled") is False:
                    cancel_existing()
                    continue
                if "offset_minutes" in prayer_setting:
                    offset = int(prayer_setting["offset_minutes"])
            due_local = prayer_times.for_anchor(anchor) + timedelta(minutes=offset)
        except (TypeError, ValueError):
            cancel_existing()
            continue

        if existing is not None:
            if existing.status == "cancelled":
                existing.status = "scheduled"
                existing.scheduled_for = due_local.astimezone(timezone.utc).replace(
                    tzinfo=None
                )
                scheduled.append(existing)
            elif existing.status in {"scheduled", "queued"}:
                due_utc = due_local.astimezone(timezone.utc).replace(tzinfo=None)
                if existing.scheduled_for != due_utc:
                    # Prayer times or the user's timezone may have changed
                    # since the row was first created. The caller will revoke
                    # the old ETA and enqueue this updated one.
                    existing.scheduled_for = due_utc
                    existing.status = "scheduled"
                # Return active rows so completion and category preferences
                # are reconciled before their delivery time.
                scheduled.append(existing)
            if group is not None:
                groups_seen.add(group[0])
            continue
        schedule = ScheduledNotification(
            user_id=user_id,
            template_id=template.id,
            local_date=local_date.isoformat(),
            scheduled_for=due_local.astimezone(timezone.utc).replace(tzinfo=None),
        )
        db.add(schedule)
        scheduled.append(schedule)
        if group is not None:
            groups_seen.add(group[0])
    db.flush()
    return scheduled


def render_template(template, *, prayer_time: datetime) -> tuple[str, str]:
    context = {"prayer_time": prayer_time.strftime("%H:%M")}
    return (
        template.title_template.format_map(context),
        template.message_template.format_map(context),
    )
