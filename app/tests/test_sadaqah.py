import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User


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
        category="charity",
        difficulty=1,
        reward_weight=1,
        verified=True,
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


def _cleanup_user_state(db, user_id: int) -> None:
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


def test_near_simultaneous_add_star_completes_once_and_spills_to_new_jar(db):
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
