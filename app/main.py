from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

import app.db.base_class

from app.api.admin_analytics import router as admin_analytics_router
from app.api.admin_charities import router as admin_charities_router
from app.api.admin_evidence import router as admin_evidence_router
from app.api.auth import router as auth_router
from app.api.charities import router as charities_router
from app.api.dashboard import router as dashboard_router
from app.api.family import router as family_router
from app.api.friday import router as friday_router
from app.api.leaderboard import router as leaderboard_router
from app.api.sadaqah import router as sadaqah_router
from app.api.streak import router as streak_router
from app.api.websocket import router as websocket_router
from app.core.config import settings
from app.core.exceptions import general_exception_handler, http_exception_handler
from app.core.logger import logger
from app.db.deps import get_db



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API startup complete")
    yield
    logger.info("API shutdown")
    


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    exception_handlers={
        HTTPException: http_exception_handler,
        Exception: general_exception_handler
    }
)
app.include_router(auth_router)
app.include_router(sadaqah_router)
app.include_router(dashboard_router)
app.include_router(streak_router)
app.include_router(leaderboard_router)
app.include_router(family_router)
app.include_router(websocket_router)
app.include_router(admin_analytics_router)
app.include_router(admin_charities_router)
app.include_router(admin_evidence_router)
app.include_router(charities_router)
app.include_router(friday_router)



@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}

