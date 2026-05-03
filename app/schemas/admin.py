from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CharityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website_url: HttpUrl
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class EvidenceCreate(BaseModel):
    act_id: int = Field(gt=0)
    source_type: str = Field(min_length=1, max_length=50)
    reference: str = Field(min_length=1, max_length=255)
    arabic_text: str | None = None
    english_text: str | None = None
    grade: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")
