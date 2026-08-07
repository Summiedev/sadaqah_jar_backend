"""Build durable, prayer-relative reminder schedules from notification templates."""

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.notifications.models import ScheduledNotification, SchedulingStrategy
from app.services.prayer_time_service import PrayerTimes


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
    db: Session, *, user_id: int, local_date: date, prayer_times: PrayerTimes
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
    for template in templates:
        config = _config(template.strategy_config)
        allowed_days = config.get("days_of_week")
        if allowed_days is not None and local_date.weekday() not in allowed_days:
            continue
        anchor = config.get("anchor")
        if not isinstance(anchor, str):
            continue
        try:
            offset = int(config.get("offset_minutes", 0))
            due_local = prayer_times.for_anchor(anchor) + timedelta(minutes=offset)
        except (TypeError, ValueError):
            continue

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
            continue
        schedule = ScheduledNotification(
            user_id=user_id,
            template_id=template.id,
            local_date=local_date.isoformat(),
            scheduled_for=due_local.astimezone(timezone.utc).replace(tzinfo=None),
        )
        db.add(schedule)
        scheduled.append(schedule)
    db.flush()
    return scheduled


def render_template(template, *, prayer_time: datetime) -> tuple[str, str]:
    context = {"prayer_time": prayer_time.strftime("%H:%M")}
    return (
        template.title_template.format_map(context),
        template.message_template.format_map(context),
    )
