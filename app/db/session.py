from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

_engine_kwargs = {"pool_pre_ping": True}
if urlparse(settings.DATABASE_URL).scheme.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

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
