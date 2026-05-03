from sqlalchemy import Date, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime, timezone
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    hashed_password: Mapped[str] = mapped_column(String(255))

    friday_reminder: Mapped[bool] = mapped_column(Boolean, default=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    role: Mapped[str] = mapped_column(String, default="USER")

    evidence_mode: Mapped[bool] = mapped_column(Boolean, default=True)

    jars = relationship(
        "Jar",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    logs = relationship("SadaqahLog", backref="user")