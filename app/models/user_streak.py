from datetime import date, datetime, timezone
from sqlalchemy import Integer, ForeignKey, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserStreak(Base):
    __tablename__ = "user_streaks"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        index=True,
        nullable=False
    )

    current_streak: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    longest_streak: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    last_completed_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=lambda: datetime.now(timezone.utc),
    onupdate=lambda: datetime.now(timezone.utc),
)