import json
import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")

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


def _clean(email: str, username: str):
    db = SessionLocal()
    db.query(User).filter(User.email == email).delete()
    db.query(User).filter(User.username == username).delete()
    db.commit()
    db.close()


def _mock_tokeninfo_response(email="google-user@example.com", google_id="google-123456789"):
    return {
        "sub": google_id,
        "email": email,
        "email_verified": "true",
        "given_name": "Google",
        "family_name": "User",
        "aud": "test-google-client-id",
        "iss": "https://accounts.google.com",
    }


def _mock_client(email="google-user@example.com", google_id="google-123456789"):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = _mock_tokeninfo_response(email, google_id)
    mock_client = MagicMock()
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response
    return mock_client


def test_google_auth_creates_new_user(db):
    email = "google-new@example.com"
    google_id = "google-new-123"
    _clean(email, "google-new-user")
    with patch("app.users.service.httpx.Client", _mock_client(email, google_id)):
        response = client.post(
            f"{API}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_google_auth_logs_in_existing_google_user(db):
    email = "google-return@example.com"
    google_id = "google-return-456"
    _clean(email, "google-return-user")
    with patch("app.users.service.httpx.Client", _mock_client(email, google_id)):
        first = client.post(
            f"{API}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )
    assert first.status_code == 200
    first_user_id = client.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {first.json()['access_token']}"},
    ).json()["user_id"]

    with patch("app.users.service.httpx.Client", _mock_client(email, google_id)):
        second = client.post(
            f"{API}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )
    assert second.status_code == 200
    second_user_id = client.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    ).json()["user_id"]
    assert first_user_id == second_user_id


def test_google_auth_links_existing_email_user(db):
    email = "google-link@example.com"
    google_id = "google-link-789"
    username = "google-link-user"
    _clean(email, username)
    reg = client.post(
        f"{API}/auth/register",
        json={"username": username, "email": email, "password": "StrongPass123!"},
    )
    assert reg.status_code == 200

    with patch("app.users.service.httpx.Client", _mock_client(email, google_id)):
        response = client.post(
            f"{API}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )
    assert response.status_code == 200

    token = response.json()["access_token"]
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_google_auth_rejects_unverified_email(db):
    bad_response = {
        "sub": "google-999",
        "email": "unverified@example.com",
        "email_verified": "false",
        "aud": "test-google-client-id",
    }
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = bad_response
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response

    with patch("app.users.service.httpx.Client", mock_client):
        response = client.post(
            f"{API}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )
    assert response.status_code == 401


def test_google_auth_rejects_audience_mismatch(db):
    bad_response = {
        "sub": "google-999",
        "email": "audience-bad@example.com",
        "email_verified": "true",
        "aud": "wrong-client-id",
    }
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = bad_response
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response

    with patch("app.users.service.httpx.Client", mock_client):
        response = client.post(
            f"{API}/auth/google",
            json={"id_token": "valid-google-id-token"},
        )
    assert response.status_code == 401


def test_google_auth_rejects_invalid_token(db):
    with patch("app.users.service.httpx.Client") as mock_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("invalid")
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        response = client.post(
            f"{API}/auth/google",
            json={"id_token": "invalid-token"},
        )
    assert response.status_code == 401
