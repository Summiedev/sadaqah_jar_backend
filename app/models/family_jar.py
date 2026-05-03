from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime, timezone

class FamilyJar(Base):
    __tablename__ = "family_jars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255))

    invite_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    capacity: Mapped[int] = mapped_column(Integer, default=33)

    current_stars: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    group_current_streak = mapped_column(Integer, default=0)

    group_longest_streak = mapped_column(Integer, default=0)

    members = relationship("FamilyJarMember", back_populates="family_jar")

    logs = relationship("FamilyJarLog", back_populates="family_jar")