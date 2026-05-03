from sqlalchemy import String, Enum, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from enum import Enum as PyEnum


class SadaqahCategory(PyEnum):
    general = "general"
    dhikr = "dhikr"
    community = "community"
    donation = "donation"


class SadaqahAct(Base):
    __tablename__ = "sadaqah_acts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[SadaqahCategory] = mapped_column(
        Enum(SadaqahCategory, native_enum=False),
        nullable=False
    )

    verified: Mapped[bool] = mapped_column(Boolean, default=True)

    is_ramadan_only: Mapped[bool] = mapped_column(Boolean, default=False)

    ramadan_multiplier: Mapped[int] = mapped_column(Integer, default=1)

    difficulty: Mapped[int] = mapped_column(Integer, default=1)

    reward_weight: Mapped[int] = mapped_column(Integer, default=1)

    evidences = relationship(
        "Evidence",
        cascade="all, delete-orphan",
        back_populates="act"
    )
    logs = relationship("SadaqahLog", backref="act")