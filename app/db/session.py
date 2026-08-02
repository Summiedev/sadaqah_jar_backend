from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

_scheme = urlparse(settings.DATABASE_URL).scheme
_engine_kwargs = {"pool_pre_ping": True}

if _scheme.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Bound the pool so a burst of concurrent requests can't open unlimited
    # connections, and reclaim a connection that can't be checked out within
    # 30s instead of blocking the request forever. ``pool_recycle`` drops
    # stale server-side connections.
    _engine_kwargs.update(
        pool_size=getattr(settings, "DB_POOL_SIZE", 10),
        max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 20),
        pool_timeout=getattr(settings, "DB_POOL_TIMEOUT", 30),
        pool_recycle=1800,
    )
    # Postgres statement-timeout backstop: any single query that runs longer
    # than this is aborted by the server, so a slow/blocked query (e.g. under
    # the add-star FOR UPDATE path) can't hold a pool connection indefinitely
    # and starve every other request.
    if _scheme.startswith("postgres"):
        statement_timeout_ms = getattr(settings, "DB_STATEMENT_TIMEOUT_MS", 15000)
        _engine_kwargs["connect_args"] = {
            "options": f"-c statement_timeout={statement_timeout_ms}"
        }

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)  # avoids dead DB connections

"""
A session is:

A temporary pass to talk to the database

Every request gets: one session,does work,then throws it away

"""
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,  # don't automatically save changes
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
