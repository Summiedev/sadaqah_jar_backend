from pydantic import BaseModel
from typing import Optional


class SadaqahActBase(BaseModel):
    title: str
    description: Optional[str]
    reward: int


class SadaqahActResponse(SadaqahActBase):
    id: int

    class Config:
        from_attributes = True