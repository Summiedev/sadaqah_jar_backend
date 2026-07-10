from pathlib import Path
import os
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_TEST_DB_DIR = PROJECT_ROOT / ".pytest_tmp"
_TEST_DB_DIR.mkdir(exist_ok=True)
_TEST_DB_PATH = _TEST_DB_DIR / "test.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_DB_PATH.as_posix()}"

from app.db.base import Base
import app.models  # noqa: F401 - register ORM models before create_all
from app.db.session import engine

Base.metadata.create_all(bind=engine)
