from fastapi import HTTPException


PDF_MIME = "application/pdf"
EPUB_MIME = "application/epub+zip"
JPEG_MIME = "image/jpeg"
PNG_MIME = "image/png"


def detect_mime(content: bytes) -> str | None:
    if content.startswith(b"%PDF-"):
        return PDF_MIME
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG_MIME
    if content.startswith(b"\xff\xd8\xff"):
        return JPEG_MIME
    if (
        content.startswith(b"PK\x03\x04")
        and b"mimetypeapplication/epub+zip" in content[:128]
    ):
        return EPUB_MIME
    return None


def validate_file_content(
    content: bytes,
    *,
    allowed_mimes: set[str],
    max_size_bytes: int,
    label: str,
) -> str:
    if not content:
        raise HTTPException(status_code=400, detail=f"{label} is empty")
    if len(content) > max_size_bytes:
        mb = max_size_bytes // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"{label} exceeds {mb} MB")
    detected = detect_mime(content)
    if detected not in allowed_mimes:
        raise HTTPException(status_code=400, detail=f"{label} type is not allowed")
    return detected
