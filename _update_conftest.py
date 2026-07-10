path = 'app/tests/conftest.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

old = '''from pathlib import Path
import sys
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _get_local_db_url() -> str:
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "summie")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    dbname = os.environ.get("DB_NAME", "sadaqah_jar")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def pytest_sessionstart() -> None:
    db_url = _get_local_db_url()
    os.environ["DATABASE_URL"] = db_url

    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(os.path.join(str(PROJECT_ROOT), "alembic.ini"))
    command.upgrade(alembic_cfg, "head")'''

new = '''from pathlib import Path
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

from app.db.base import Base
import app.models  # noqa: F401 - register ORM models before create_all
from app.db.session import engine

Base.metadata.create_all(bind=engine)'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('updated helper script')
else:
    print('helper script already differs; no change')
