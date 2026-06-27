from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.leaderboard_season import LeaderboardSeason


def get_leaderboard_season(db: Session, season_name: str) -> LeaderboardSeason | None:
    return (
        db.query(LeaderboardSeason)
        .filter(func.lower(LeaderboardSeason.season_name) == season_name.lower())
        .first()
    )
