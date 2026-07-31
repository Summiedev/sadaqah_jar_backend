from pydantic import BaseModel


class BookBookmarkResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    chapter_number: int | None
    created_at: str

    class Config:
        from_attributes = True


class BookmarkCreateRequest(BaseModel):
    book_id: int
    chapter_number: int | None = None


class BookmarkListResponse(BaseModel):
    total: int
    data: list[BookBookmarkResponse]