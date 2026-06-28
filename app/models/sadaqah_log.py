import datetime
from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SadaqahLog(Base):
    __tablename__ = "sadaqah_logs"

    __table_args__ = (
        UniqueConstraint("user_id", "act_id", "date", name="unique_daily_log"),
        UniqueConstraint("user_id", "request_id", name="unique_sadaqah_log_request"),
        Index("idx_user_date", "user_id", "date"),
        Index("idx_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    act_id: Mapped[int] = mapped_column(
        ForeignKey("sadaqah_acts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    response_current_stars: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    response_capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    response_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False, index=True
    )

    stars_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    friday_boost: Mapped[bool] = mapped_column(Boolean, default=False)

    ramadan_bonus: Mapped[bool] = mapped_column(Boolean, default=False)
