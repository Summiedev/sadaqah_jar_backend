from pathlib import Path
import os

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent

_TEST_DB_DIR = PROJECT_ROOT / ".pytest_tmp"
_TEST_DB_DIR.mkdir(exist_ok=True)
_TEST_DB_PATH = _TEST_DB_DIR / "test.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

# Seed the settings the app requires at import time so the suite is hermetic:
# it must run in CI (or a fresh clone) without a populated `.env` and without
# touching the real database/redis. `setdefault` means a real value in the
# environment still wins, but a missing one no longer aborts collection with a
# pydantic ValidationError. DATABASE_URL is forced to a throwaway sqlite file.
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ.setdefault("APP_NAME", "mizan-test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")


@pytest.fixture(autouse=True)
def _in_memory_rate_limiter(monkeypatch):
    """Run the rate limiter against an in-memory store instead of Redis.

    The suite has no Redis, and the sensitive auth endpoints deliberately fail
    *closed* (``fail_open=False``) so a Redis outage can't silently disable
    their limits — which means without a backend every login/register call
    returns 429. Rather than weaken that production behavior, we swap the Lua
    script for a Python implementation with identical sliding-window semantics
    so the real limit logic is still exercised, just deterministically and
    per-test.

    Patching ``_get_script`` (not the public functions) is what makes this work
    regardless of where ``check_rate_limit``/``check_rate_limit_key`` were
    imported: both resolve ``_get_script`` from their own module globals at call
    time.
    """
    from app.core import rate_limit

    store: dict[str, list[tuple[float, str]]] = {}

    def _fake_script(keys=None, args=None):
        key = keys[0]
        now, period, limit, member = args
        now = float(now)
        period = float(period)
        limit = int(limit)
        entries = store.setdefault(key, [])
        cutoff = now - period
        entries[:] = [(score, m) for score, m in entries if score > cutoff]
        if len(entries) >= limit:
            return 0
        entries.append((now, member))
        return 1

    monkeypatch.setattr(rate_limit, "_get_script", lambda: _fake_script)
    yield


