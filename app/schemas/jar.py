from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class JarBase(BaseModel):
    current_stars: int
    capacity: int


class JarResponse(JarBase):
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True