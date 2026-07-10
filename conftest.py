from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent
_TEST_DB_DIR = PROJECT_ROOT / ".pytest_tmp"
_TEST_DB_DIR.mkdir(exist_ok=True)
_TEST_DB_PATH = _TEST_DB_DIR / "test.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_DB_PATH.as_posix()}"
