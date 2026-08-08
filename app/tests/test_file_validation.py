import pytest
from fastapi import HTTPException

from app.services.file_validation import (
    JPEG_MIME,
    PDF_MIME,
    PNG_MIME,
    detect_mime,
    validate_file_content,
)


def test_detects_file_magic_bytes():
    assert detect_mime(b"%PDF-1.7\n") == PDF_MIME
    assert detect_mime(b"\x89PNG\r\n\x1a\nrest") == PNG_MIME
    assert detect_mime(b"\xff\xd8\xff\xe0rest") == JPEG_MIME


def test_rejects_extension_spoofed_content():
    with pytest.raises(HTTPException) as exc:
        validate_file_content(
            b"<script>alert(1)</script>",
            allowed_mimes={PDF_MIME},
            max_size_bytes=1024,
            label="Book file",
        )
    assert exc.value.status_code == 400
