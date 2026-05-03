from sqlalchemy import Date, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime, timezone

class FamilyJarLog(Base):
    __tablename__ = "family_jar_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_jar_id: Mapped[int] = mapped_column(Integer, ForeignKey("family_jars.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    act_id: Mapped[int] = mapped_column(Integer, ForeignKey("sadaqah_acts.id"))
    stars_added: Mapped[int] = mapped_column(Integer, default=1)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    family_jar = relationship("FamilyJar", back_populates="logs")