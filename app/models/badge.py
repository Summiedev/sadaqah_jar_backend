from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column
from app.db.base import Base


class Badge(Base):
    __tablename__ = "badges"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String)
    description = mapped_column(String)
