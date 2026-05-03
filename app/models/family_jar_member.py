from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime, timezone



class FamilyJarMember(Base):
    __tablename__ = "family_jar_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_jar_id: Mapped[int] = mapped_column(Integer, ForeignKey("family_jars.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(50), default="member")  # admin/creator/member
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    family_jar = relationship("FamilyJar", back_populates="members")