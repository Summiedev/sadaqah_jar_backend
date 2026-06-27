import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.api import leaderboard as leaderboard_api
from app.main import app
from app.db.session import SessionLocal
from app.models.leaderboard_season import LeaderboardSeason

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_ramadan_leaderboard_returns_empty_outside_configured_window(db, monkeypatch):
    season = LeaderboardSeason(
        season_name="Ramadan",
        start_date=date(2026, 2, 17),
        end_date=date(2026, 3, 18),
    )
    db.add(season)
    db.commit()
    db.refresh(season)

    monkeypatch.setattr(leaderboard_api, "_utc_today", lambda: date(2026, 6, 18))

    try:
        response = client.get("/leaderboard/ramadan")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        db.delete(season)
        db.commit()
