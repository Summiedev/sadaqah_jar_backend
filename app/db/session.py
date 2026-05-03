# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)# avoids dead DB connections
'''
A session is:

A temporary pass to talk to the database

Every request gets: one session,does work,then throws it away

'''
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False, # don't automatically save changes
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()