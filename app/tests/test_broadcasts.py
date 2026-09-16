"""Regression tests for admin broadcasts and user receipts."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.broadcast import Broadcast, BroadcastReceipt
from app.models.user import Role, User

client = TestClient(app)
API = "/api/v1"


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _user(db, role: Role) -> User:
    suffix = uuid4().hex
    user = User(
        username=f"broadcast_{suffix}",
        email=f"broadcast_{suffix}@test.com",
        hashed_password=hash_password("TestPass123"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "role": user.role.name})
    return {"Authorization": f"Bearer {token}"}


def test_admin_broadcast_is_visible_then_stays_dismissed(db):
    admin = _user(db, Role.ADMIN)
    member = _user(db, Role.USER)
    response = client.post(
        f"{API}/admin/broadcasts/",
        json={
            "title": "A helpful update",
            "body": "A short announcement for the community.",
            "display_mode": "until_dismissed",
        },
        headers=_headers(admin),
    )
    assert response.status_code == 201
    broadcast_id = response.json()["id"]

    active = client.get(f"{API}/broadcasts/active", headers=_headers(member))
    assert active.status_code == 200
    assert [item["id"] for item in active.json()["data"]] == [broadcast_id]

    viewed = client.post(
        f"{API}/broadcasts/{broadcast_id}/view", headers=_headers(member)
    )
    dismissed = client.post(
        f"{API}/broadcasts/{broadcast_id}/dismiss", headers=_headers(member)
    )
    assert viewed.status_code == 200
    assert dismissed.status_code == 200

    after = client.get(f"{API}/broadcasts/active", headers=_headers(member))
    assert after.status_code == 200
    assert after.json()["data"] == []

    admin_list = client.get(
        f"{API}/admin/broadcasts/", headers=_headers(admin)
    )
    assert admin_list.status_code == 200
    row = next(item for item in admin_list.json()["data"] if item["id"] == broadcast_id)
    assert row["analytics"] == {"views": 1, "dismissals": 1, "clicks": 0}

    db.query(BroadcastReceipt).filter_by(broadcast_id=broadcast_id).delete(
        synchronize_session=False
    )
    db.query(Broadcast).filter_by(id=broadcast_id).delete(synchronize_session=False)
    db.delete(admin)
    db.delete(member)
    db.commit()


def test_non_admin_cannot_manage_broadcasts(db):
    member = _user(db, Role.USER)
    response = client.get(f"{API}/admin/broadcasts/", headers=_headers(member))
    assert response.status_code == 403
    db.delete(member)
    db.commit()


def test_admin_analytics_overview_returns_aggregate_contract(db):
    admin = _user(db, Role.ADMIN)
    response = client.get(
        f"{API}/admin/analytics/overview",
        headers=_headers(admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"range", "users", "activity", "daily_active_users"}
    assert {"total", "new_today", "new_this_week", "new_this_month"} <= set(
        payload["users"]
    )
    assert {
        "journey_events",
        "reflections",
        "sadaqah_records",
        "books_saved",
        "donation_intents",
        "broadcast_views",
        "broadcast_clicks",
    } <= set(payload["activity"])
    assert isinstance(payload["daily_active_users"], list)

    db.delete(admin)
    db.commit()
