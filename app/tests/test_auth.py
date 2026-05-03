import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    yield db
    db.close()


def test_register_and_login(db):
    # Clean user first
    db.query(User).filter(User.email=="test2@example.com").delete()
    db.commit()

    # Register
    response = client.post("/auth/register", json={
        "username": "test-user",
        "email": "test2@example.com",
        "password": "StrongPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Login
    response = client.post("/auth/login", json={
        "email": "test2@example.com",
        "password": "StrongPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Protected route
    token = data["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "user_id" in response.json()