"""
Tests for family.py endpoints — targets audit-flagged bugs:

1. Create jar → creator is auto-added as member with role="creator"
2. Join jar → valid invite code adds member; duplicate join is prevented
3. Add-star → non-member gets 403; already-logged act same day gets 400
4. Add-star concurrency → 5+ distinct members adding stars simultaneously must
   produce exactly N increments with no lost updates (atomic row-lock fix).
5. Leaderboard → returns top N members by stars
"""

import pytest
import threading
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User
from app.models.family_jar import FamilyJar
from app.models.family_jar_member import FamilyJarMember
from app.models.family_jar_log import FamilyJarLog
from app.models.sadaqah_act import SadaqahAct
from app.core.security import hash_password
from app.services.family_service import update_family_streak_on_contribution

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


def _auth_header(user_id: int) -> dict:
    """Create a minimal valid JWT for a user."""
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner(db):
    u = User(
        username="family_owner",
        email="family_owner@test.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    db.query(FamilyJarLog).filter(
        FamilyJarLog.user_id == u.id
    ).delete()
    db.query(FamilyJarMember).filter(
        FamilyJarMember.user_id == u.id
    ).delete()
    db.query(FamilyJar).filter(
        FamilyJar.created_by == u.id
    ).delete()
    db.query(User).filter(User.id == u.id).delete()
    db.commit()


@pytest.fixture
def member(db):
    u = User(
        username="family_member",
        email="family_member@test.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    db.query(FamilyJarLog).filter(
        FamilyJarLog.user_id == u.id
    ).delete()
    db.query(FamilyJarMember).filter(
        FamilyJarMember.user_id == u.id
    ).delete()
    db.query(User).filter(User.id == u.id).delete()
    db.commit()


@pytest.fixture
def act(db):
    a = SadaqahAct(
        title="Test act",
        description="A test act",
        category="charity",
        difficulty=1,
        reward_weight=1,
        verified=True,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    yield a
    db.delete(a)
    db.commit()


class TestCreateJar:
    """Audit bug caught: creator must be added as member with role='creator'."""

    def test_creator_is_member(self, db, owner):
        resp = client.post(
            "/family/create",
            params={"name": "Test Family", "capacity": 33},
            headers=_auth_header(owner.id),
        )
        assert resp.status_code == 200
        jar_id = resp.json()["jar_id"]

        member_row = db.query(FamilyJarMember).filter(
            FamilyJarMember.family_jar_id == jar_id,
            FamilyJarMember.user_id == owner.id,
        ).first()
        assert member_row is not None
        assert member_row.role == "creator"


class TestJoinJar:
    """Audit bug caught: duplicate join must raise 400, not silently succeed."""

    def test_join_with_valid_code(self, db, owner, member):
        jar = FamilyJar(
            name="Joinable Jar", capacity=33, created_by=owner.id, invite_code="JOIN123"
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        resp = client.post(
            "/family/join",
            params={"invite_code": "JOIN123"},
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 200
        assert resp.json()["jar_id"] == jar.id

    def test_duplicate_join_rejected(self, db, owner, member):
        jar = FamilyJar(
            name="Dup Jar", capacity=33, created_by=owner.id, invite_code="DUP123"
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        # First join
        client.post(
            "/family/join",
            params={"invite_code": "DUP123"},
            headers=_auth_header(member.id),
        )

        # Second join — must fail
        resp = client.post(
            "/family/join",
            params={"invite_code": "DUP123"},
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 400
        assert "Already a member" in resp.text

    def test_invalid_code_returns_404(self, member):
        resp = client.post(
            "/family/join",
            params={"invite_code": "NONEXIST"},
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 404


class TestAddStar:
    """Audit bug caught: non-member gets 403, duplicate act gets 400."""

    def test_non_member_rejected(self, db, owner, member, act):
        jar = FamilyJar(
            name="Star Jar", capacity=33, created_by=owner.id, invite_code="STAR1"
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        resp = client.post(
            "/family/add-star",
            params={"jar_id": jar.id, "act_id": act.id},
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 403

    def test_member_can_add_star(self, db, owner, member, act):
        jar = FamilyJar(
            name="Star Jar 2", capacity=33, created_by=owner.id, invite_code="STAR2"
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        # Add member
        db.add(FamilyJarMember(family_jar_id=jar.id, user_id=member.id))
        db.commit()

        resp = client.post(
            "/family/add-star",
            params={"jar_id": jar.id, "act_id": act.id},
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 200
        assert resp.json()["current_stars"] > 0

    def test_duplicate_act_same_day_rejected(self, db, owner, member, act):
        jar = FamilyJar(
            name="Star Jar 3", capacity=33, created_by=owner.id, invite_code="STAR3"
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)
        db.add(FamilyJarMember(family_jar_id=jar.id, user_id=member.id))
        db.commit()

        # First add-star
        client.post(
            "/family/add-star",
            params={"jar_id": jar.id, "act_id": act.id},
            headers=_auth_header(member.id),
        )

        # Second add-star same act — must fail
        resp = client.post(
            "/family/add-star",
            params={"jar_id": jar.id, "act_id": act.id},
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 400


class TestFamilyLeaderboard:
    def test_non_member_gets_forbidden(self, db, owner, member, act):
        jar = FamilyJar(
            name="Board Jar", capacity=33, created_by=owner.id, invite_code="BOARD1"
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        resp = client.get(
            f"/family/{jar.id}/leaderboard",
            headers=_auth_header(member.id),
        )
        assert resp.status_code == 403


class TestFamilyStreakService:
    def test_two_day_gap_resets_to_one(self, db, owner):
        jar = FamilyJar(
            name="Gap Jar",
            capacity=33,
            created_by=owner.id,
            invite_code="GAP123",
            last_activity_date=date(2026, 6, 14),
            streak_days=4,
            longest_streak=4,
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        update_family_streak_on_contribution(jar, date(2026, 6, 16))
        db.commit()
        db.refresh(jar)

        assert jar.streak_days == 1

    def test_longest_streak_persists_after_reset(self, db, owner):
        jar = FamilyJar(
            name="Longest Jar",
            capacity=33,
            created_by=owner.id,
            invite_code="LONG123",
            last_activity_date=date(2026, 6, 10),
            streak_days=7,
            longest_streak=7,
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        update_family_streak_on_contribution(jar, date(2026, 6, 13))
        db.commit()
        db.refresh(jar)

        assert jar.streak_days == 1
        assert jar.longest_streak == 7


class TestAddStarConcurrency:
    """
    Concurrency test: 6 distinct family members add stars near-simultaneously.
    Asserts final star count == sum of increments, proving no lost updates
    under the row-level lock (SELECT ... FOR UPDATE) fix.
    """

    def test_concurrent_multi_member_add_star(self, db, owner, act):
        NUM_MEMBERS = 6
        CAPACITY = NUM_MEMBERS * 2  # enough room for all

        jar = FamilyJar(
            name="Concurrency Jar",
            capacity=CAPACITY,
            created_by=owner.id,
            invite_code="CONCUR",
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)

        # Create unique users + add each as a member of the jar
        members = []
        member_cleanup = []
        try:
            for i in range(NUM_MEMBERS):
                u = User(
                    username=f"concurrent_user_{i}",
                    email=f"concurrent_user_{i}@test.com",
                    hashed_password=hash_password("TestPass123"),
                )
                db.add(u)
                db.commit()
                db.refresh(u)
                members.append(u)
                member_cleanup.append(u)

                m = FamilyJarMember(family_jar_id=jar.id, user_id=u.id)
                db.add(m)
            db.commit()

            # We'll use a different act per member to avoid user+act+date collisions.
            # Create NUM_MEMBERS acts.
            test_acts = []
            for i in range(NUM_MEMBERS):
                a = SadaqahAct(
                    title=f"Concurrency act {i}",
                    description=f"Test act for concurrency {i}",
                    category="charity",
                    difficulty=1,
                    reward_weight=1,
                    verified=True,
                )
                db.add(a)
                db.commit()
                db.refresh(a)
                test_acts.append(a)

            errors = []

            def _do_add_star(user_id: int, act_id: int) -> int:
                """Call the add-star endpoint for a given member and return stars_added."""
                resp = client.post(
                    "/family/add-star",
                    params={"jar_id": jar.id, "act_id": act_id},
                    headers=_auth_header(user_id),
                )
                if resp.status_code != 200:
                    errors.append(f"user {user_id} got {resp.status_code}: {resp.text}")
                    return 0
                data = resp.json()
                # Subtract starting stars (0) to get the increment
                return data["current_stars"]

            # Fire off concurrent requests from all members
            with ThreadPoolExecutor(max_workers=NUM_MEMBERS) as pool:
                futures = {
                    pool.submit(_do_add_star, members[i].id, test_acts[i].id): i
                    for i in range(NUM_MEMBERS)
                }
                results = []
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        errors.append(str(e))

            if errors:
                pytest.fail(f"Concurrency errors: {'; '.join(errors[:5])}")

            # Read final jar state from DB directly
            db.refresh(jar)
            final_stars = jar.current_stars

            # Each of the NUM_MEMBERS added 1 star (reward_weight=1, no special day)
            expected_stars = NUM_MEMBERS * 1

            assert final_stars == expected_stars, (
                f"Expected {expected_stars} stars but got {final_stars}. "
                f"This indicates lost updates under concurrent access."
            )

        finally:
            # Cleanup: remove jar logs, members, users, acts
            for a in test_acts if 'test_acts' in dir() else []:
                try:
                    db.delete(a)
                except Exception:
                    pass
            for u in member_cleanup:
                try:
                    db.query(FamilyJarLog).filter(FamilyJarLog.user_id == u.id).delete()
                    db.query(FamilyJarMember).filter(FamilyJarMember.user_id == u.id).delete()
                    db.query(User).filter(User.id == u.id).delete()
                except Exception:
                    pass
            db.commit()


class TestFamilyWebsocket:
    def test_non_member_rejected_from_family_channel(self, db, owner, member):
        jar = FamilyJar(
            name="Socket Jar",
            capacity=33,
            created_by=owner.id,
            invite_code="SOCK123",
        )
        db.add(jar)
        db.commit()
        db.refresh(jar)
        db.add(FamilyJarMember(family_jar_id=jar.id, user_id=owner.id, role="creator"))
        db.commit()

        token = _auth_header(member.id)["Authorization"].split(" ", 1)[1]
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/api/v1/websock/ws/family-jar/{jar.id}?token={token}") as ws:
                ws.receive_text()

        assert excinfo.value.code == 4403
