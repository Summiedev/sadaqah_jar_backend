from pydantic import BaseModel, Field


class QuranSurahResponse(BaseModel):
    id: int
    name_ar: str
    name_en: str
    name_transliteration: str
    revelation_type: str
    ayah_count: int
    bismillah_pre: bool
    first_page: int | None = None
    last_page: int | None = None
    first_juz: int | None = None


class QuranArabicResponse(BaseModel):
    uthmani: str
    tajweed: str | None = None
    simple: str | None = None


class QuranTranslationResponse(BaseModel):
    edition: str
    language: str
    translator_name: str
    text: str


class QuranAudioResponse(BaseModel):
    reciter_id: str
    url: str
    start_ms: int | None = None
    end_ms: int | None = None


class QuranMetaResponse(BaseModel):
    juz: int
    hizb: int
    hizb_quarter: int | None = None
    manzil: int | None = None
    ruku: int | None = None
    page: int
    sajda: bool
    sajda_type: str | None = None


class QuranAyahResponse(BaseModel):
    verse_key: str
    surah_id: int
    ayah_number: int
    arabic: QuranArabicResponse
    translation: QuranTranslationResponse | None = None
    transliteration: str | None = None
    audio: list[QuranAudioResponse] = []
    meta: QuranMetaResponse


class QuranPageResponse(BaseModel):
    page_number: int
    image_url: str | None = None
    local_storage_key: str | None = None
    ayahs: list[QuranAyahResponse]


class QuranSearchResult(BaseModel):
    verse_key: str
    surah_id: int
    ayah_number: int
    page_number: int
    surah_name: str
    text: str
    translation: str | None = None


class QuranBookmarkCreate(BaseModel):
    verse_key: str | None = Field(None, pattern=r"^\d{1,3}:\d{1,3}$")
    page_number: int | None = Field(None, ge=1, le=604)


class QuranBookmarkResponse(QuranBookmarkCreate):
    id: int
