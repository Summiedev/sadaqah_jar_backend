"""Regression tests for the aggregated Journey history read model."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.journey.models import JourneyReflection
from app.main import app
from app.models.user import Role, User
from app.sadaqah.models import ActivityCompletion, ActivityContext, ActivityType

client = TestClient(app)
API = "/api/v1"


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_history_contains_existing_reflections_and_activity(db):
    suffix = uuid4().hex
    user = User(
        username=f"history_{suffix}",
        email=f"history_{suffix}@test.com",
        hashed_password=hash_password("TestPass123"),
        role=Role.USER,
    )
    db.add(user)
    db.flush()
    occurred = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(
        JourneyReflection(
            user_id=user.id,
            title="A quiet note",
            body="I made time to reflect.",
            mood="grateful",
            date=occurred,
        )
    )
    db.add(
        ActivityCompletion(
            user_id=user.id,
            activity_type=ActivityType.KINDNESS,
            context=ActivityContext.PERSONAL,
            completed_at=occurred,
            note="Checked in on a neighbour",
        )
    )
    db.commit()
    token = create_access_token({"sub": str(user.id), "role": user.role.name})

    response = client.get(
        f"{API}/journey/history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    items = response.json()["data"]
    assert {item["kind"] for item in items} >= {"reflection", "activity"}
    assert any(item["title"] == "A quiet note" for item in items)
    assert any("kindness" in item["title"] for item in items)

    db.query(ActivityCompletion).filter_by(user_id=user.id).delete(
        synchronize_session=False
    )
    db.query(JourneyReflection).filter_by(user_id=user.id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()
