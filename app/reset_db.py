from app.db.base import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)
print("Database reset complete!")