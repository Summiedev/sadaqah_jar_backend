import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User

client = TestClient(app)

API = "/api/v1"


@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    yield db
    db.close()


def _clean(email, username):
    db = SessionLocal()
    db.query(User).filter(User.email == email).delete()
    db.query(User).filter(User.username == username).delete()
    db.commit()
    db.close()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_and_login(db):
    _clean("test2@example.com", "test-user")
    response = client.post(
        f"{API}/auth/register",
        json={
            "username": "test-user",
            "email": "test2@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data and "refresh_token" in data

    token = data["access_token"]
    response = client.get(f"{API}/auth/me", headers=_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == "test2@example.com"

    response = client.get(f"{API}/users/me", headers=_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"]
    assert body["role"] == "USER"
    assert body["mode"] == "BOTH"

    # login
    response = client.post(
        f"{API}/auth/login",
        json={"email": "test2@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_register_username_taken_returns_409(db):
    _clean("collision1@example.com", "collision-user")
    _clean("collision2@example.com", "collision-user")
    first = client.post(
        f"{API}/auth/register",
        json={
            "username": "collision-user",
            "email": "collision1@example.com",
            "password": "StrongPass123!",
        },
    )
    assert first.status_code == 200
    second = client.post(
        f"{API}/auth/register",
        json={
            "username": "collision-user",
            "email": "collision2@example.com",
            "password": "StrongPass123!",
        },
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "auth.username_taken"


def test_invalid_credentials(db):
    _clean("badlogin@example.com", "badlogin-user")
    client.post(
        f"{API}/auth/register",
        json={
            "username": "badlogin-user",
            "email": "badlogin@example.com",
            "password": "StrongPass123!",
        },
    )
    response = client.post(
        f"{API}/auth/login",
        json={"email": "badlogin@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_refresh_and_logout_flow(db):
    _clean("flow@example.com", "flow-user")
    reg = client.post(
        f"{API}/auth/register",
        json={
            "username": "flow-user",
            "email": "flow@example.com",
            "password": "StrongPass123!",
        },
    )
    refresh = reg.json()["refresh_token"]
    token = reg.json()["access_token"]

    # refresh rotates and returns new tokens
    refreshed = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh != refresh

    # old refresh is now revoked
    replay = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert replay.status_code == 401

    # logout current device
    response = client.post(f"{API}/auth/logout", json={"refresh_token": new_refresh})
    assert response.status_code == 204

    # sessions list reflects logout
    sessions = client.get(f"{API}/users/me/sessions", headers=_headers(token))
    assert sessions.status_code == 200


def test_mode_sync(db):
    _clean("mode@example.com", "mode-user")
    reg = client.post(
        f"{API}/auth/register",
        json={
            "username": "mode-user",
            "email": "mode@example.com",
            "password": "StrongPass123!",
        },
    )
    token = reg.json()["access_token"]
    for mode in ("PERSONAL", "FAMILY", "BOTH"):
        response = client.patch(
            f"{API}/users/mode", json={"mode": mode}, headers=_headers(token)
        )
        assert response.status_code == 200
        assert response.json()["mode"] == mode


def test_preferences_sync(db):
    _clean("prefs@example.com", "prefs-user")
    reg = client.post(
        f"{API}/auth/register",
        json={
            "username": "prefs-user",
            "email": "prefs@example.com",
            "password": "StrongPass123!",
        },
    )
    token = reg.json()["access_token"]
    response = client.patch(
        f"{API}/users/me/preferences",
        json={
            "theme": "dark",
            "language": "ar",
            "timezone": "Africa/Lagos",
            "friday_reminder": True,
        },
        headers=_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["theme"] == "dark"
    assert response.json()["timezone"] == "Africa/Lagos"
    assert response.json()["notification_preferences"]["friday_reminder"] is True
    profile = client.get(f"{API}/users/me", headers=_headers(token))
    assert profile.json()["friday_reminder"] is True


def test_devices_and_push_token(db):
    _clean("device@example.com", "device-user")
    reg = client.post(
        f"{API}/auth/register",
        json={
            "username": "device-user",
            "email": "device@example.com",
            "password": "StrongPass123!",
        },
    )
    token = reg.json()["access_token"]
    push = client.post(
        f"{API}/users/me/push-token",
        json={
            "device_id": "dev-abc",
            "platform": "ios",
            "device_name": "iPhone",
            "push_token": "tok-xyz",
        },
        headers=_headers(token),
    )
    assert push.status_code == 200

    devices = client.get(f"{API}/users/me/devices", headers=_headers(token))
    assert devices.status_code == 200
    assert len(devices.json()) == 1
    assert devices.json()[0]["device_id"] == "dev-abc"
    assert devices.json()[0]["has_push_token"] is True
    device_record_id = devices.json()[0]["id"]

    # update device
    upd = client.patch(
        f"{API}/users/me/devices/{device_record_id}",
        json={"device_name": "My iPhone"},
        headers=_headers(token),
    )
    assert upd.status_code == 200

    # delete device
    delete = client.delete(
        f"{API}/users/me/devices/{device_record_id}", headers=_headers(token)
    )
    assert delete.status_code == 204


def test_logout_all_devices(db):
    _clean("multi@example.com", "multi-user")
    reg = client.post(
        f"{API}/auth/register",
        json={
            "username": "multi-user",
            "email": "multi@example.com",
            "password": "StrongPass123!",
        },
    )
    token = reg.json()["access_token"]
    # create a second session via another login
    client.post(
        f"{API}/auth/login",
        json={"email": "multi@example.com", "password": "StrongPass123!"},
    )

    sessions = client.get(f"{API}/users/me/sessions", headers=_headers(token))
    assert len(sessions.json()) >= 2

    response = client.delete(f"{API}/users/me/sessions", headers=_headers(token))
    assert response.status_code == 204

    sessions = client.get(f"{API}/users/me/sessions", headers=_headers(token))
    assert all(not s["is_current"] for s in sessions.json())
