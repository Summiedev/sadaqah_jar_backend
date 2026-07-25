from pathlib import Path
import os
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
os.environ.setdefault("APP_NAME", "Mizan Test API")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/15")
os.environ.setdefault("JWT_SECRET", "test-secret-must-have-at-least-32-characters")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

_alembic = Config(str(PROJECT_ROOT / "alembic.ini"))
_alembic.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
_alembic.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
command.upgrade(_alembic, "head")
