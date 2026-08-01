"""Notification event handlers.

Subscribes to domain events and enqueues notifications with proper
idempotency keys, rapid-fire deduplication, and async retry-safe delivery.

Every handler here is a thin, synchronous, non-blocking function called from
business services. It does NOT talk to the database or push provider
directly. Instead it:

  1. Runs a Redis SETNX dedup check to suppress rapid-fire duplicate events.
  2. Enqueues ``deliver_event_notification`` (a retry-with-backoff Celery
     task) which performs preference checks, quiet-hours logging, the
     idempotent DB insert, and the push send on a worker.

This keeps the request thread fast and ensures every event-triggered push
goes through the same retry-safe path as scheduled reminders.
"""

import logging

from app.notifications.dedup import claim_event, release_event

logger = logging.getLogger(__name__)


def _enqueue(
    *,
    user_id: int,
    title: str,
    message: str,
    category: str,
    notification_type: str,
    idempotency_key: str,
    action: str | None = None,
    data: dict | None = None,
) -> bool:
    """Deduplicate then enqueue an event notification for async delivery.

    Returns True if the notification was enqueued, False if it was
    suppressed as a rapid-fire duplicate.

    The Celery task is imported lazily to avoid a circular import between
    the notifications package and the tasks package at module load time.
    """
    # Rapid-fire dedup: suppress genuinely duplicate events within the
    # dedup window. The DB idempotency key still guards against duplicate
    # rows on retry, so this is a best-effort fast-path suppression.
    if not claim_event(idempotency_key):
        logger.info(
            "Suppressed rapid-fire duplicate event %s for user %s",
            idempotency_key,
            user_id,
        )
        return False

    from app.tasks.notification_tasks import deliver_event_notification

    try:
        deliver_event_notification.delay(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            notification_type=notification_type,
            idempotency_key=idempotency_key,
            action=action,
            data=data,
        )
    except Exception:
        # If enqueue fails (broker down), release the dedup claim so a later
        # retry of the same event is allowed through before the TTL expires.
        logger.exception(
            "Failed to enqueue event notification %s for user %s",
            idempotency_key,
            user_id,
        )
        release_event(idempotency_key)
        raise
    return True


# ---------------------------------------------------------------------------
# Streak Reminder
# ---------------------------------------------------------------------------


def on_streak_broken(user_id: int, previous_streak: int) -> None:
    """Notify a user when their streak is broken."""
    _enqueue(
        user_id=user_id,
        title="Streak broken",
        message=f"Your {previous_streak}-day streak was broken. Start a new one today!",
        category="journey",
        notification_type="streak_reminder",
        idempotency_key=f"streak:{user_id}:{previous_streak}",
        action="streak",
    )


def on_streak_milestone(user_id: int, streak: int) -> None:
    """Notify a user when they hit a streak milestone (7, 30, 100)."""
    _enqueue(
        user_id=user_id,
        title=f"{streak}-day streak!",
        message=f"Amazing! You've maintained a {streak}-day streak. Keep going!",
        category="journey",
        notification_type="streak_reminder",
        idempotency_key=f"streak_milestone:{user_id}:{streak}",
        action="streak",
    )


# ---------------------------------------------------------------------------
# Goal Progress
# ---------------------------------------------------------------------------


def on_goal_completed(user_id: int, goal_id: int, goal_title: str) -> None:
    """Notify a user when a goal is completed."""
    _enqueue(
        user_id=user_id,
        title="Goal completed!",
        message=f"Congratulations! You completed '{goal_title}'.",
        category="journey",
        notification_type="goal_progress",
        idempotency_key=f"goal_completed:{user_id}:{goal_id}",
        action=f"goal:{goal_id}",
    )


def on_goal_milestone(user_id: int, goal_id: int, milestone: int) -> None:
    """Notify a user when a goal crosses a milestone (25%, 50%, 75%, 100%)."""
    _enqueue(
        user_id=user_id,
        title=f"Goal {milestone}% complete",
        message=f"Your goal is {milestone}% complete. Keep up the great work!",
        category="journey",
        notification_type="goal_progress",
        idempotency_key=f"goal_milestone:{user_id}:{goal_id}:{milestone}",
        action=f"goal:{goal_id}",
    )


# ---------------------------------------------------------------------------
# Family Activity
# ---------------------------------------------------------------------------


def on_family_activity(
    user_id: int, family_id: int, actor_name: str, activity_type: str
) -> None:
    """Notify a family member of new activity in their family."""
    messages = {
        "prayer_request": f"{actor_name} shared a new prayer request.",
        "reflection": f"{actor_name} shared a new reflection.",
        "goal_completed": f"{actor_name} completed a family goal!",
        "member_joined": f"{actor_name} joined the family.",
        "act_added": f"{actor_name} added an act to the family jar.",
    }
    message = messages.get(activity_type, f"{actor_name} shared an update.")
    _enqueue(
        user_id=user_id,
        title="Family update",
        message=message,
        category="family",
        notification_type="family_activity",
        idempotency_key=f"family_activity:{user_id}:{family_id}:{activity_type}",
        action=f"family:{family_id}",
    )


# ---------------------------------------------------------------------------
# Achievement / Badge
# ---------------------------------------------------------------------------


def on_badge_earned(user_id: int, badge_id: int, badge_name: str) -> None:
    """Notify a user when they earn a badge."""
    _enqueue(
        user_id=user_id,
        title="Achievement unlocked!",
        message=f"You earned the '{badge_name}' badge!",
        category="journey",
        notification_type="achievement",
        idempotency_key=f"badge:{user_id}:{badge_id}",
        action="achievements",
    )


# ---------------------------------------------------------------------------
# Invitation
# ---------------------------------------------------------------------------


def on_invitation_created(
    user_id: int, family_id: int, family_name: str, invite_code: str
) -> None:
    """Notify a user that they've been invited to a family."""
    _enqueue(
        user_id=user_id,
        title="Family invitation",
        message=f"You've been invited to join '{family_name}'.",
        category="family",
        notification_type="invitation",
        idempotency_key=f"invitation:{user_id}:{family_id}:{invite_code}",
        action="invitations",
    )


# ---------------------------------------------------------------------------
# Reading Progress
# ---------------------------------------------------------------------------


def on_reading_milestone(
    user_id: int, book_id: int, book_title: str, chapter: int
) -> None:
    """Notify a user when they reach a reading milestone."""
    _enqueue(
        user_id=user_id,
        title="Reading milestone",
        message=f"You've reached chapter {chapter} of '{book_title}'.",
        category="reading",
        notification_type="reading_progress",
        idempotency_key=f"reading:{user_id}:{book_id}:{chapter}",
        action=f"book:{book_id}",
    )
