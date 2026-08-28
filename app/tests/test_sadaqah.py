import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal, engine
from app.family.models import Family, FamilyMember, FamilyRole, FamilySettings
from app.main import app
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User
from app.goals.models import GoalStatus, UserGoal


client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def _auth_header(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _create_user(db, prefix: str) -> User:
    user = User(
        username=f"{prefix}_{uuid.uuid4().hex[:8]}",
        email=f"{prefix}_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_act(db, title: str) -> SadaqahAct:
    act = SadaqahAct(
        title=title,
        description="Test act",
        category="general",
        difficulty=1,
        reward_weight=1,
        verified=True,
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


def _create_family(db, owner_id: int, prefix: str) -> Family:
    family = Family(
        name=f"{prefix} family",
        invite_code=f"{prefix}-{uuid.uuid4().hex[:12]}",
        created_by=owner_id,
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    db.add(FamilyMember(family_id=family.id, user_id=owner_id, role=FamilyRole.OWNER))
    db.add(FamilySettings(family_id=family.id))
    db.commit()
    db.refresh(family)
    return family


def _cleanup_family(db, family_id: int) -> None:
    db.query(FamilySettings).filter(FamilySettings.family_id == family_id).delete(
        synchronize_session=False
    )
    db.query(FamilyMember).filter(FamilyMember.family_id == family_id).delete(
        synchronize_session=False
    )
    db.query(Family).filter(Family.id == family_id).delete(synchronize_session=False)
    db.commit()


def _cleanup_user_state(db, user_id: int) -> None:
    db.query(UserGoal).filter(UserGoal.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(SadaqahLog).filter(SadaqahLog.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(Jar).filter(Jar.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


def test_add_star_request_id_is_idempotent(db):
    user = _create_user(db, "idempotent")
    act = _create_act(db, "Idempotent act")
    request_id = uuid.uuid4().hex

    try:
        first = client.post(
            "/api/v1/sadaqah/jar/add-star",
            params={"act_id": act.id, "request_id": request_id},
            headers=_auth_header(user.id),
        )
        second = client.post(
            "/api/v1/sadaqah/jar/add-star",
            params={"act_id": act.id, "request_id": request_id},
            headers=_auth_header(user.id),
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

        active_jar = (
            db.query(Jar)
            .filter(Jar.user_id == user.id, Jar.completed_at.is_(None))
            .first()
        )
        assert active_jar is not None
        assert active_jar.current_stars == first.json()["current_stars"]
    finally:
        db.query(SadaqahAct).filter(SadaqahAct.id == act.id).delete(
            synchronize_session=False
        )
        _cleanup_user_state(db, user.id)


def test_add_star_restores_personal_goal_progress_after_relogin(db):
    user = _create_user(db, "goal-persistence")
    act = _create_act(db, "Persistent goal act")
    goal = UserGoal(
        user_id=user.id,
        title="Keep going",
        acts_target=10,
        acts_done=0,
        month=None,
    )
    db.add(goal)
    db.commit()

    try:
        response = client.post(
            "/api/v1/sadaqah/jar/add-star",
            params={"act_id": act.id, "request_id": uuid.uuid4().hex},
            headers=_auth_header(user.id),
        )

        assert response.status_code == 200
        db.refresh(goal)
        # Friday and seasonal boosts can make one act worth more than one
        # star. The persistence contract is that both durable records agree.
        assert response.json()["current_stars"] == goal.acts_done
        assert goal.acts_done > 0
    finally:
        db.query(UserGoal).filter(UserGoal.user_id == user.id).delete(
            synchronize_session=False
        )
        db.commit()
        db.query(SadaqahAct).filter(SadaqahAct.id == act.id).delete(
            synchronize_session=False
        )
        _cleanup_user_state(db, user.id)


def test_personal_goal_allows_only_one_active_goal(db):
    user = _create_user(db, "single-active-goal")
    headers = _auth_header(user.id)
    try:
        first = client.post(
            "/api/v1/goals",
            json={"title": "Read daily", "acts_target": 10},
            headers=headers,
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/goals",
            json={"title": "Give sadaqah", "acts_target": 5},
            headers=headers,
        )
        assert second.status_code == 409
        assert "active goal" in second.json()["error"]["message"]
        assert (
            db.query(UserGoal)
            .filter(
                UserGoal.user_id == user.id,
                UserGoal.status == GoalStatus.ACTIVE,
            )
            .count()
            == 1
        )
    finally:
        _cleanup_user_state(db, user.id)


def test_completed_goal_can_be_followed_by_a_new_goal(db):
    user = _create_user(db, "completed-then-next-goal")
    headers = _auth_header(user.id)
    try:
        first = client.post(
            "/api/v1/goals",
            json={"title": "First goal", "acts_target": 1},
            headers=headers,
        )
        assert first.status_code == 201
        first_id = first.json()["data"]["id"]

        completed = client.patch(
            f"/api/v1/goals/{first_id}/status",
            json={"status": "completed"},
            headers=headers,
        )
        assert completed.status_code == 200

        second = client.post(
            "/api/v1/goals",
            json={"title": "Second goal", "acts_target": 20},
            headers=headers,
        )
        assert second.status_code == 201
        assert second.json()["data"]["status"] == GoalStatus.ACTIVE.value

        history = client.get("/api/v1/goals", headers=headers)
        assert history.status_code == 200
        goals = history.json()["data"]["goals"]
        assert {goal["status"] for goal in goals} == {
            GoalStatus.ACTIVE.value,
            GoalStatus.COMPLETED.value,
        }
    finally:
        _cleanup_user_state(db, user.id)


def test_replacing_goal_preserves_history_and_creates_one_active_goal(db):
    user = _create_user(db, "replace-goal")
    headers = _auth_header(user.id)
    try:
        first = client.post(
            "/api/v1/goals",
            json={"title": "Old intention", "acts_target": 10},
            headers=headers,
        )
        assert first.status_code == 201
        first_id = first.json()["data"]["id"]

        replacement = client.post(
            f"/api/v1/goals/{first_id}/replace",
            json={"title": "New intention", "acts_target": 25},
            headers=headers,
        )
        assert replacement.status_code == 201
        assert replacement.json()["data"]["title"] == "New intention"

        db.expire_all()
        old = db.get(UserGoal, first_id)
        assert old is not None
        assert old.status == GoalStatus.REPLACED
        assert (
            db.query(UserGoal)
            .filter(
                UserGoal.user_id == user.id,
                UserGoal.status == GoalStatus.ACTIVE,
                UserGoal.deleted_at.is_(None),
            )
            .count()
            == 1
        )
    finally:
        _cleanup_user_state(db, user.id)

def test_activity_completion_rejects_non_member_family_id(db):
    owner = _create_user(db, "activity_family_owner")
    outsider = _create_user(db, "activity_family_outsider")
    family = _create_family(db, owner.id, "activity-completion")

    try:
        response = client.post(
            "/api/v1/activities/completions",
            json={
                "activity_type": "kindness",
                "context": "family",
                "family_id": family.id,
            },
            headers=_auth_header(outsider.id),
        )

        assert response.status_code == 403
    finally:
        _cleanup_family(db, family.id)
        _cleanup_user_state(db, owner.id)
        _cleanup_user_state(db, outsider.id)


def test_activity_session_rejects_non_member_family_id(db):
    owner = _create_user(db, "session_family_owner")
    outsider = _create_user(db, "session_family_outsider")
    family = _create_family(db, owner.id, "activity-session")

    try:
        response = client.post(
            "/api/v1/activities/sessions",
            json={
                "activity_type": "prayer",
                "context": "family",
                "family_id": family.id,
            },
            headers=_auth_header(outsider.id),
        )

        assert response.status_code == 403
    finally:
        _cleanup_family(db, family.id)
        _cleanup_user_state(db, owner.id)
        _cleanup_user_state(db, outsider.id)


def test_near_simultaneous_add_star_completes_once_and_spills_to_new_jar(db):
    if engine.dialect.name == "sqlite":
        pytest.skip("Concurrency semantics require PostgreSQL row locking.")

    user = _create_user(db, "race")
    act_one = _create_act(db, "Race act one")
    act_two = _create_act(db, "Race act two")
    jar = Jar(user_id=user.id, current_stars=1, capacity=2)
    db.add(jar)
    db.commit()
    db.refresh(jar)

    barrier = Barrier(2)

    def submit(act_id: int):
        barrier.wait()
        return client.post(
            "/api/v1/sadaqah/jar/add-star",
            params={"act_id": act_id, "request_id": uuid.uuid4().hex},
            headers=_auth_header(user.id),
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(submit, [act_one.id, act_two.id]))

        assert all(response.status_code == 200 for response in responses)

        payloads = [response.json() for response in responses]
        assert sorted(item["current_stars"] for item in payloads) == [1, 2]
        assert any(item["completed_at"] is not None for item in payloads)
        assert any(item["completed_at"] is None for item in payloads)

        jars = db.query(Jar).filter(Jar.user_id == user.id).order_by(Jar.id.asc()).all()
        assert len(jars) == 2
        completed_jar = next(j for j in jars if j.completed_at is not None)
        active_jar = next(j for j in jars if j.completed_at is None)
        assert completed_jar.current_stars == 2
        assert active_jar.current_stars == 1
    finally:
        db.query(SadaqahLog).filter(SadaqahLog.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(SadaqahAct).filter(SadaqahAct.id.in_([act_one.id, act_two.id])).delete(
            synchronize_session=False
        )
        _cleanup_user_state(db, user.id)
