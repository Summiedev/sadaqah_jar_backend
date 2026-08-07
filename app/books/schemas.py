from pydantic import BaseModel


class BookChapterRead(BaseModel):
    id: int
    book_id: int
    chapter_number: int
    title: str
    content: str
    reading_time_minutes: int


class BookPageRead(BaseModel):
    id: int
    book_id: int
    page_number: int
    image_url: str
    image_type: str | None = None


class BookRead(BaseModel):
    id: int
    title: str
    author: str
    description: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    file_type: str | None = None
    file_format: str | None = None
    category: str
    language: str
    published: bool
    sort_order: int
    chapter_count: int = 0
    total_reading_time: int = 0
    page_count: int = 0


class BookDetail(BookRead):
    chapters: list[BookChapterRead] = []
    pages: list[BookPageRead] = []


class BookCreate(BaseModel):
    title: str
    author: str
    description: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    file_type: str | None = None
    file_format: str | None = None
    category: str
    language: str = "en"
    published: bool = True
    sort_order: int = 0


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    file_type: str | None = None
    file_format: str | None = None
    category: str | None = None
    language: str | None = None
    published: bool | None = None
    sort_order: int | None = None


class BookChapterCreate(BaseModel):
    chapter_number: int
    title: str
    content: str
    reading_time_minutes: int = 5


class BookChapterUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    reading_time_minutes: int | None = None


class BookListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[BookRead]
