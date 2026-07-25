"""Tests for Books API.

Frontend source of truth for the following calls:
- GET  /books
- GET  /books/{bookId}
- GET  /books/{bookId}/chapters
- GET  /books/{bookId}/chapters/{chapterNumber}
- GET  /admin/books/
- POST /admin/books/
- PATCH /admin/books/{bookId}
- DELETE /admin/books/{bookId}
- GET  /admin/books/{bookId}/chapters
- POST /admin/books/{bookId}/chapters
- PATCH /admin/books/{bookId}/chapters/{chapterId}
- DELETE /admin/books/{bookId}/chapters/{chapterId}
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User, Role
from app.books.models import Book, BookChapter

client = TestClient(app)

API = "/api/v1"


def _headers(user_id: int, role: str = "USER") -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user_id), 'role': role})}"}


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


def _create_user(db, username, email, role=Role.USER) -> User:
    u = User(username=username, email=email, hashed_password=hash_password("TestPass123"), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _clean_books(db):
    db.query(BookChapter).delete(synchronize_session=False)
    db.query(Book).delete(synchronize_session=False)
    db.commit()


def test_list_books_returns_published_only(db):
    _clean_books(db)
    published = Book(title="Published Book", author="Author", category="faith", published=True, sort_order=1)
    draft = Book(title="Draft Book", author="Author", category="faith", published=False, sort_order=2)
    db.add_all([published, draft])
    db.commit()

    resp = client.get(f"{API}/books/")
    assert resp.status_code == 200
    data = resp.json()
    titles = [b["title"] for b in data["data"]]
    assert "Published Book" in titles
    assert "Draft Book" not in titles
    _clean_books(db)


def test_get_book_detail(db):
    _clean_books(db)
    book = Book(title="Detail Test", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    ch1 = BookChapter(book_id=book.id, chapter_number=1, title="Ch1", content="Content 1", reading_time_minutes=5)
    ch2 = BookChapter(book_id=book.id, chapter_number=2, title="Ch2", content="Content 2", reading_time_minutes=8)
    db.add_all([ch1, ch2])
    db.commit()

    resp = client.get(f"{API}/books/{book.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["title"] == "Detail Test"
    assert body["data"]["chapter_count"] == 2
    assert len(body["data"]["chapters"]) == 2
    _clean_books(db)


def test_get_book_404(db):
    _clean_books(db)
    resp = client.get(f"{API}/books/99999")
    assert resp.status_code == 404


def test_list_chapters(db):
    _clean_books(db)
    book = Book(title="Chapter Test", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    ch1 = BookChapter(book_id=book.id, chapter_number=1, title="Ch1", content="C1", reading_time_minutes=5)
    db.add(ch1)
    db.commit()

    resp = client.get(f"{API}/books/{book.id}/chapters")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    _clean_books(db)


def test_get_chapter_by_number(db):
    _clean_books(db)
    book = Book(title="Single Chapter", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    ch = BookChapter(book_id=book.id, chapter_number=1, title="Only Chapter", content="Content", reading_time_minutes=3)
    db.add(ch)
    db.commit()

    resp = client.get(f"{API}/books/{book.id}/chapters/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["title"] == "Only Chapter"
    assert body["data"]["content"] == "Content"
    _clean_books(db)


def test_get_chapter_404(db):
    _clean_books(db)
    book = Book(title="No Chapters", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    resp = client.get(f"{API}/books/{book.id}/chapters/1")
    assert resp.status_code == 404
    _clean_books(db)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


def test_admin_list_books_includes_drafts(db):
    _clean_books(db)
    admin = _create_user(db, "admin_books", "admin_books@test.com", role=Role.ADMIN)
    published = Book(title="Admin Book", author="Author", category="faith", published=True, sort_order=1)
    db.add_all([published, Book(title="Draft", author="Author", category="faith", published=False, sort_order=2)])
    db.commit()

    resp = client.get(f"{API}/admin/books/", headers=_headers(admin.id, "ADMIN"))
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.json()["data"]]
    assert "Admin Book" in titles
    assert "Draft" in titles
    _clean_books(db)


def test_admin_create_book(db):
    _clean_books(db)
    admin = _create_user(db, "admin_create", "admin_create@test.com", role=Role.ADMIN)
    payload = {
        "title": "New Admin Book",
        "author": "Admin Author",
        "description": "A test book",
        "category": "faith",
        "language": "en",
        "published": True,
        "sort_order": 1,
    }
    resp = client.post(f"{API}/admin/books/", json=payload, headers=_headers(admin.id, "ADMIN"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Admin Book"
    assert data["author"] == "Admin Author"
    assert data["category"] == "faith"
    _clean_books(db)


def test_admin_update_book(db):
    _clean_books(db)
    admin = _create_user(db, "admin_update", "admin_update@test.com", role=Role.ADMIN)
    book = Book(title="Old Title", author="Old Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    resp = client.patch(
        f"{API}/admin/books/{book.id}",
        json={"title": "New Title", "description": "Updated"},
        headers=_headers(admin.id, "ADMIN"),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["description"] == "Updated"
    _clean_books(db)


def test_admin_delete_book(db):
    _clean_books(db)
    admin = _create_user(db, "admin_delete", "admin_delete@test.com", role=Role.ADMIN)
    book = Book(title="To Delete", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)
    book_id = book.id

    resp = client.delete(f"{API}/admin/books/{book_id}", headers=_headers(admin.id, "ADMIN"))
    assert resp.status_code == 200

    db.expire_all()
    deleted = db.query(Book).filter(Book.id == book_id).first()
    assert deleted is not None
    assert deleted.deleted_at is not None
    _clean_books(db)


def test_admin_create_chapter(db):
    _clean_books(db)
    admin = _create_user(db, "admin_chap", "admin_chap@test.com", role=Role.ADMIN)
    book = Book(title="Book for Chapters", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    payload = {
        "chapter_number": 1,
        "title": "First Chapter",
        "content": "This is chapter one.",
        "reading_time_minutes": 10,
    }
    resp = client.post(f"{API}/admin/books/{book.id}/chapters", json=payload, headers=_headers(admin.id, "ADMIN"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "First Chapter"
    assert data["reading_time_minutes"] == 10
    _clean_books(db)


def test_admin_list_chapters(db):
    _clean_books(db)
    admin = _create_user(db, "admin_listchap", "admin_listchap@test.com", role=Role.ADMIN)
    book = Book(title="Multi Chapter Book", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    db.add(BookChapter(book_id=book.id, chapter_number=1, title="Ch1", content="C1", reading_time_minutes=5))
    db.add(BookChapter(book_id=book.id, chapter_number=2, title="Ch2", content="C2", reading_time_minutes=8))
    db.commit()

    resp = client.get(f"{API}/admin/books/{book.id}/chapters", headers=_headers(admin.id, "ADMIN"))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2
    _clean_books(db)


def test_admin_update_chapter(db):
    _clean_books(db)
    admin = _create_user(db, "admin_updchap", "admin_updchap@test.com", role=Role.ADMIN)
    book = Book(title="Update Chapter", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    ch = BookChapter(book_id=book.id, chapter_number=1, title="Old Title", content="Old", reading_time_minutes=5)
    db.add(ch)
    db.commit()
    db.refresh(ch)

    resp = client.patch(
        f"{API}/admin/books/{book.id}/chapters/{ch.id}",
        json={"title": "New Title", "content": "New Content", "reading_time_minutes": 15},
        headers=_headers(admin.id, "ADMIN"),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["content"] == "New Content"
    assert resp.json()["reading_time_minutes"] == 15
    _clean_books(db)


def test_admin_delete_chapter(db):
    _clean_books(db)
    admin = _create_user(db, "admin_delchap", "admin_delchap@test.com", role=Role.ADMIN)
    book = Book(title="Delete Chapter", author="Author", category="faith", published=True, sort_order=1)
    db.add(book)
    db.commit()
    db.refresh(book)

    ch = BookChapter(book_id=book.id, chapter_number=1, title="To Delete", content="C", reading_time_minutes=5)
    db.add(ch)
    db.commit()
    db.refresh(ch)
    ch_id = ch.id

    resp = client.delete(f"{API}/admin/books/{book.id}/chapters/{ch_id}", headers=_headers(admin.id, "ADMIN"))
    assert resp.status_code == 200

    db.expire_all()
    found = db.query(BookChapter).filter(BookChapter.id == ch_id).first()
    assert found is None
    _clean_books(db)


def test_non_admin_cannot_access_admin_books(db):
    user = _create_user(db, "non_admin", "non_admin@test.com", role=Role.USER)
    resp = client.get(f"{API}/admin/books/", headers=_headers(user.id, "USER"))
    assert resp.status_code == 403
