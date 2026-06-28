from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeaderboardSeason(Base):
    __tablename__ = "leaderboard_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
