from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    source_type: str
    reference: str
    grade: str | None = None
    arabic_text: str | None = None
    english_text: str | None = None
    is_verified: bool


class ActDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    difficulty: int
    reward_weight: int
    estimated_time_minutes: int | None = None
    evidence: EvidenceResponse | None = None

    class Config:
        from_attributes = True


class ActListResponse(BaseModel):
    id: int
    title: str
    category: str
    difficulty: int

    class Config:
        from_attributes = True


class ActPageResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[ActListResponse]
