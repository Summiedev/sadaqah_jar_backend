import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    yield db
    db.close()


def test_register_and_login(db):
    # Clean user first
    db.query(User).filter(User.email == "test2@example.com").delete()
    db.commit()

    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "test-user",
            "email": "test2@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Login
    response = client.post(
        "/api/v1/auth/login", json={"email": "test2@example.com", "password": "StrongPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Protected route
    token = data["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "user_id" in response.json()


def test_register_username_taken_returns_409(db):
    db.query(User).filter(User.username == "collision-user").delete()
    db.query(User).filter(
        User.email.in_(["collision1@example.com", "collision2@example.com"])
    ).delete()
    db.commit()

    first = client.post(
        "/api/v1/auth/register",
        json={
            "username": "collision-user",
            "email": "collision1@example.com",
            "password": "StrongPass123!",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/register",
        json={
            "username": "collision-user",
            "email": "collision2@example.com",
            "password": "StrongPass123!",
        },
    )
    assert second.status_code == 409
    payload = second.json()
    assert payload["message"]["code"] == "username_taken"
