import datetime
from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SadaqahLog(Base):
    __tablename__ = "sadaqah_logs"

    __table_args__ = (
        UniqueConstraint("user_id", "act_id", "date", name="unique_daily_log"),
        Index("idx_user_date", "user_id", "date"),
        Index("idx_date", "date"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    act_id: Mapped[int] = mapped_column(
        ForeignKey("sadaqah_acts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False
    )

    stars_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )

    friday_boost: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    ramadan_bonus: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )