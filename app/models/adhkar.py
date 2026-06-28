from enum import Enum as PyEnum

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimeOfDay(PyEnum):
    morning = "morning"
    evening = "evening"


class Adhkar(Base):
    __tablename__ = "adhkar"

    id: Mapped[int] = mapped_column(primary_key=True)

    text_arabic: Mapped[str] = mapped_column(Text, nullable=False)
    text_translation: Mapped[str] = mapped_column(Text, nullable=False)

    time_of_day: Mapped[TimeOfDay] = mapped_column(
        Enum(TimeOfDay, native_enum=False),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(String, nullable=False)

    repeat_count: Mapped[int] = mapped_column(Integer, default=1)
