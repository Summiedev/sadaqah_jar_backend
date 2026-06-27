from sqlalchemy import Date, Integer, String, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime, timezone


class FamilyJarLog(Base):
    __tablename__ = "family_jar_logs"

    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_family_jar_log_request"),
        Index("ix_family_jar_log_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_jar_id: Mapped[int] = mapped_column(Integer, ForeignKey("family_jars.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    act_id: Mapped[int] = mapped_column(Integer, ForeignKey("sadaqah_acts.id"))
    stars_added: Mapped[int] = mapped_column(Integer, default=1)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    request_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    response_current_stars: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    response_capacity: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    response_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    family_jar = relationship("FamilyJar", back_populates="logs")