"""
Tests for streak_service.py - targets the exact bugs flagged in the audit:

1. `update_streak()`: first-call initialisation creates streak with current=1,
   longest=1. Second-call on the same day is idempotent.
2. Missed-day reset: if last_completed_date < yesterday, current_streak resets to 1.
3. Longest-streak persistence: current surpassing longest updates longest.
4. `validate_streak()`: if more than 1 day has passed, resets to 0 (gap detection).
"""

from datetime import date, timedelta

import pytest
from app.db.session import SessionLocal
from app.models.user_streak import UserStreak
from app.models.user import User
from app.services.streak_service import update_streak, validate_streak
from app.core.security import hash_password


# Reuse the same fixture pattern as test_auth.py
@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


@pytest.fixture
def user(db):
    u = User(
        username="streak_test_user",
        email="streak_test@example.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    db.query(UserStreak).filter(UserStreak.user_id == u.id).delete()
    db.query(User).filter(User.id == u.id).delete()
    db.commit()


class TestUpdateStreak:
    """Audit bug caught: initial streak must set both current and longest to 1."""

    def test_first_call_creates_streak(self, db, user):
        s = update_streak(db, user.id)
        assert s.current_streak == 1
        assert s.longest_streak == 1
        assert s.last_completed_date == date.today()

    def test_same_day_is_idempotent(self, db, user):
        s1 = update_streak(db, user.id)
        s2 = update_streak(db, user.id)
        assert s2.current_streak == s1.current_streak
        assert s2.longest_streak == s1.longest_streak

    def test_consecutive_day_increments(self, db, user):
        s1 = update_streak(db, user.id)
        previous_current = s1.current_streak
        # Manually set last_completed_date to yesterday
        s1.last_completed_date = date.today() - timedelta(days=1)
        db.commit()

        s2 = update_streak(db, user.id)
        assert s2.current_streak == previous_current + 1

    def test_missed_day_resets_to_one(self, db, user):
        s1 = update_streak(db, user.id)
        # Set last_completed_date to 3 days ago (gap)
        s1.last_completed_date = date.today() - timedelta(days=3)
        db.commit()

        s2 = update_streak(db, user.id)
        assert s2.current_streak == 1  # reset

    def test_longest_streak_persists(self, db, user):
        """Audit bug caught: longest_streak must survive a reset."""
        # Build streak to 5 by backdating
        s = update_streak(db, user.id)
        s.current_streak = 5
        s.longest_streak = 5
        s.last_completed_date = date.today() - timedelta(days=3)
        db.commit()

        # Miss days -> reset
        s2 = update_streak(db, user.id)
        assert s2.current_streak == 1
        assert s2.longest_streak == 5  # preserved


class TestValidateStreak:
    """Audit bug caught: validate_streak detects gaps and zeroes out."""

    def test_no_gap_does_nothing(self, db, user):
        s = update_streak(db, user.id)
        validate_streak(db, user.id)
        db.refresh(s)
        assert s.current_streak == 1

    def test_gap_resets_to_zero(self, db, user):
        s = update_streak(db, user.id)
        s.last_completed_date = date.today() - timedelta(days=5)
        db.commit()

        validate_streak(db, user.id)
        db.refresh(s)
        assert s.current_streak == 0
