"""Tests for event-driven notification delivery.

Covers the three areas the audit flagged as unverified:

1. Celery task registration — both scheduled and event-driven task modules
   must be registered on the worker, otherwise ``deliver_event_notification``
   silently never runs.
2. Rapid-fire event deduplication — the Redis SETNX layer must suppress a
   duplicate event within the TTL window and fail open when Redis is down.
3. Retry safety + idempotency — a retried delivery must not create duplicate
   in-app notification rows.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.notifications import event_handlers
from app.notifications.models import Notification
from app.users.models import User, UserPreference
from app.core.security import create_access_token


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


@pytest.fixture
def user(db):
    u = User(
        username="deliver_test",
        email="deliver_test@example.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    db.query(Notification).filter(Notification.user_id == u.id).delete()
    db.query(UserPreference).filter(UserPreference.user_id == u.id).delete()
    db.query(User).filter(User.id == u.id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# 1. Celery task registration
# ---------------------------------------------------------------------------


class TestTaskRegistration:
    def test_event_delivery_task_registered(self):
        """deliver_event_notification must be registered on the Celery app.

        Regression guard for the original bug: autodiscover alone left this
        task unregistered because the module name did not match the default
        related_name, so events were enqueued to a task the worker did not
        know about.
        """
        from app.core.celery_app import celery_app

        assert (
            "app.tasks.notification_tasks.deliver_event_notification"
            in celery_app.tasks
        )

    def test_scheduled_tasks_registered(self):
        from app.core.celery_app import celery_app

        assert (
            "app.tasks.scheduled_tasks.deliver_scheduled_notification"
            in celery_app.tasks
        )
        assert "app.tasks.scheduled_tasks.generate_daily_acts" in celery_app.tasks


def test_notification_templates_require_admin(db):
    user = User(
        username="template_non_admin",
        email="template_non_admin@example.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    try:
        response = TestClient(app).get(
            "/api/v1/notifications/templates",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in {401, 403}
    finally:
        db.query(User).filter(User.id == user.id).delete()
        db.commit()


def test_authenticated_test_push_uses_real_fcm_delivery(user):
    """The preferences test button must exercise FCM, not only the inbox."""
    token = create_access_token({"sub": str(user.id)})
    with patch(
        "app.notifications.router.send_push_notification",
        return_value=1,
    ) as send_push:
        response = TestClient(app).post(
            "/api/v1/notifications/test-push",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["delivered"] == 1
    send_push.assert_called_once()


def test_authenticated_test_push_reports_missing_device(user):
    token = create_access_token({"sub": str(user.id)})
    with patch(
        "app.notifications.router.send_push_notification",
        return_value=0,
    ):
        response = TestClient(app).post(
            "/api/v1/notifications/test-push",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 503
    assert "No active device" in response.json()["error"]["message"]


def test_preference_update_refreshes_current_day_schedule(user):
    """Enabling reminders must not wait for the next daily beat run."""
    token = create_access_token({"sub": str(user.id)})
    with patch(
        "app.notifications.router.schedule_user_aware_reminders.apply_async"
    ) as refresh:
        response = TestClient(app).put(
            "/api/v1/notifications/preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={"all_enabled": True, "frequency": "medium"},
        )

    assert response.status_code == 200
    refresh.assert_called_once_with(args=[user.id], queue="reminders")


# ---------------------------------------------------------------------------
# 2. Rapid-fire event deduplication
# ---------------------------------------------------------------------------


class TestDedup:
    def test_claim_first_wins(self):
        from app.notifications import dedup

        fake_redis = MagicMock()
        # First claim succeeds (SET NX returns True), second returns None.
        fake_redis.set.side_effect = [True, None]
        with patch.object(dedup, "redis_client", fake_redis):
            assert dedup.claim_event("evt-1") is True
            assert dedup.claim_event("evt-1") is False

    def test_claim_fails_open_on_redis_error(self):
        import redis as redis_lib

        from app.notifications import dedup

        fake_redis = MagicMock()
        fake_redis.set.side_effect = redis_lib.RedisError("down")
        with patch.object(dedup, "redis_client", fake_redis):
            # Fail-open: a Redis outage must never silently drop notifications.
            assert dedup.claim_event("evt-2") is True

    def test_empty_key_allowed(self):
        from app.notifications import dedup

        assert dedup.claim_event("") is True


# ---------------------------------------------------------------------------
# 3. Enqueue path: dedup + async handoff
# ---------------------------------------------------------------------------


class TestEnqueue:
    def test_enqueue_suppresses_duplicate(self):
        with patch.object(event_handlers, "claim_event", return_value=False):
            fake_task = MagicMock()
            with patch(
                "app.tasks.notification_tasks.deliver_event_notification",
                fake_task,
            ):
                result = event_handlers._enqueue(
                    user_id=1,
                    title="t",
                    message="m",
                    category="journey",
                    notification_type="goal_progress",
                    idempotency_key="dup-key",
                )
        assert result is False
        fake_task.delay.assert_not_called()

    def test_enqueue_dispatches_when_claimed(self):
        with patch.object(event_handlers, "claim_event", return_value=True):
            fake_task = MagicMock()
            with patch(
                "app.tasks.notification_tasks.deliver_event_notification",
                fake_task,
            ):
                result = event_handlers._enqueue(
                    user_id=1,
                    title="t",
                    message="m",
                    category="journey",
                    notification_type="goal_progress",
                    idempotency_key="claim-key",
                )
        assert result is True
        fake_task.delay.assert_called_once()

    def test_enqueue_releases_claim_on_broker_failure_without_failing_action(self):
        with patch.object(event_handlers, "claim_event", return_value=True):
            with patch.object(event_handlers, "release_event") as release:
                fake_task = MagicMock()
                fake_task.delay.side_effect = RuntimeError("broker down")
                with patch(
                    "app.tasks.notification_tasks.deliver_event_notification",
                    fake_task,
                ):
                    result = event_handlers._enqueue(
                        user_id=1,
                        title="t",
                        message="m",
                        category="journey",
                        notification_type="goal_progress",
                        idempotency_key="broker-fail-key",
                    )
                assert result is False
                release.assert_called_once_with("broker-fail-key")


# ---------------------------------------------------------------------------
# 4. Retry safety + idempotency in the delivery task body
# ---------------------------------------------------------------------------


class TestDeliveryIdempotency:
    def test_retry_does_not_duplicate_notification(self, db, user):
        """Running the delivery body twice with the same key yields one row.

        Simulates a retry: the second invocation must return the existing
        row via the idempotency key rather than inserting a duplicate.
        """
        from app.services.notification_service import create_notification

        key = f"goal_completed:{user.id}:999"
        create_notification(
            db,
            user.id,
            title="Goal completed!",
            message="Congratulations!",
            category="journey",
            idempotency_key=key,
        )
        create_notification(
            db,
            user.id,
            title="Goal completed!",
            message="Congratulations!",
            category="journey",
            idempotency_key=key,
        )
        count = (
            db.query(Notification)
            .filter(
                Notification.user_id == user.id,
                Notification.idempotency_key == key,
            )
            .count()
        )
        assert count == 1

    def test_delivery_respects_disabled_category(self, db, user):
        """When a category is disabled, no in-app row is created."""
        pref = db.get(UserPreference, user.id)
        if pref is None:
            pref = UserPreference(user_id=user.id)
            db.add(pref)
        pref.notification_preferences = json.dumps(
            {"categories": {"journey": {"in_app": False, "push": False}}}
        )
        db.commit()

        from app.notifications.preferences import is_category_enabled

        assert is_category_enabled(db, user.id, "journey", channel="in_app") is False

    def test_push_channel_is_not_blocked_when_in_app_channel_is_disabled(
        self, db, user
    ):
        pref = db.get(UserPreference, user.id)
        if pref is None:
            pref = UserPreference(user_id=user.id)
            db.add(pref)
        pref.notification_preferences = json.dumps(
            {"categories": {"journey": {"in_app": False, "push": True}}}
        )
        db.commit()

        from app.tasks.notification_tasks import deliver_event_notification

        with patch(
            "app.tasks.notification_tasks.send_push_notification",
            return_value=1,
        ) as send_push:
            deliver_event_notification.run(
                user.id,
                "A gentle reminder",
                "Return when you are ready.",
                "journey",
                "goal_progress",
                f"push-only:{user.id}",
            )

        send_push.assert_called_once()
        assert (
            db.query(Notification)
            .filter(Notification.idempotency_key == f"push-only:{user.id}")
            .count()
            == 0
        )


def test_viewing_notification_sets_read_timestamp_without_delivery_side_effect(db, user):
    notification = Notification(
        user_id=user.id,
        category="reflection",
        title="A quiet pause",
        message="Write one honest line when you are ready.",
        status="created",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    token = create_access_token({"sub": str(user.id)})

    response = TestClient(app).patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    db.refresh(notification)
    assert notification.is_read is True
    assert notification.read_at is not None
    assert notification.delivered_at is None
