"""Tests for notification preferences, quiet hours, and idempotency."""

import json
from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.notifications.models import Notification
from app.notifications.preferences import (
    is_category_enabled,
    is_in_quiet_hours,
    should_delay_for_quiet_hours,
)
from app.services.notification_service import create_notification
from app.users.models import User, UserPreference


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


@pytest.fixture
def user(db):
    u = User(
        username="pref_test",
        email="pref_test@example.com",
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


def _set_prefs(db, user, prefs: dict):
    pref = db.get(UserPreference, user.id)
    if pref is None:
        pref = UserPreference(user_id=user.id)
        db.add(pref)
    pref.notification_preferences = json.dumps(prefs)
    db.commit()


class TestCategoryEnabled:
    def test_defaults_to_enabled(self, db, user):
        assert is_category_enabled(db, user.id, "prayer") is True

    def test_disabled_category(self, db, user):
        _set_prefs(db, user, {"categories": {"prayer": False}})
        assert is_category_enabled(db, user.id, "prayer") is False

    def test_channel_specific(self, db, user):
        _set_prefs(db, user, {"categories": {"prayer": {"push": False, "in_app": True}}})
        assert is_category_enabled(db, user.id, "prayer", channel="push") is False
        assert is_category_enabled(db, user.id, "prayer", channel="in_app") is True

    def test_global_channel_toggle(self, db, user):
        _set_prefs(db, user, {"push_enabled": False})
        assert is_category_enabled(db, user.id, "prayer") is False


class TestQuietHours:
    def test_no_quiet_hours(self, db, user):
        assert is_in_quiet_hours(db, user.id) is False

    def test_inside_quiet_hours(self, db, user):
        _set_prefs(db, user, {"quiet_hours": {"enabled": True, "start": "00:00", "end": "23:59"}})
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert is_in_quiet_hours(db, user.id, now=now) is True

    def test_outside_quiet_hours(self, db, user):
        _set_prefs(db, user, {"quiet_hours": {"enabled": True, "start": "22:00", "end": "07:00"}})
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert is_in_quiet_hours(db, user.id, now=now) is False

    def test_overnight_quiet_hours(self, db, user):
        _set_prefs(db, user, {"quiet_hours": {"enabled": True, "start": "22:00", "end": "07:00"}})
        now = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
        assert is_in_quiet_hours(db, user.id, now=now) is True

    def test_security_exempt(self, db, user):
        _set_prefs(db, user, {"quiet_hours": {"enabled": True, "start": "00:00", "end": "23:59"}})
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert should_delay_for_quiet_hours(db, user.id, "security", now=now) is False
        assert should_delay_for_quiet_hours(db, user.id, "prayer", now=now) is True


class TestIdempotency:
    def test_duplicate_key_returns_existing(self, db, user):
        n1 = create_notification(
            db, user.id, title="Test", message="Hello", idempotency_key="test-key-1"
        )
        n2 = create_notification(
            db, user.id, title="Test", message="Hello", idempotency_key="test-key-1"
        )
        assert n1.id == n2.id
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user.id, Notification.idempotency_key == "test-key-1")
            .count()
        )
        assert count == 1

    def test_different_keys_create_separate(self, db, user):
        n1 = create_notification(
            db, user.id, title="A", message="One", idempotency_key="key-a"
        )
        n2 = create_notification(
            db, user.id, title="B", message="Two", idempotency_key="key-b"
        )
        assert n1.id != n2.id