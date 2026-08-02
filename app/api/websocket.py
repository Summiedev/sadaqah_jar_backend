import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.ws_manager import manager
from app.core.security import decode_access_token
from app.family.repository import get_member
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from app.models.user import User

router = APIRouter(prefix="/websock", tags=["websocket"])
logger = logging.getLogger(__name__)



def get_user_from_token(token: str, db: Session):
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            return None
        return db.query(User).filter(User.id == int(sub)).first()
    except (JWTError, TypeError, ValueError):
        return None


@router.websocket("/ws/jar/{user_id}")
async def jar_ws(websocket: WebSocket, user_id: int, token: str = Query(None)):
    if not token:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        user = get_user_from_token(token, db)
        if user is None or user.id != user_id:
            await websocket.close(code=4001)
            return
    finally:
        db.close()

    if not await manager.connect(user_id, websocket):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        # Any other error (broken frame, transport reset) must still unregister
        # the socket so it can't leak in the connection manager.
        logger.warning("ws jar loop error for user %s", user_id, exc_info=True)
    finally:
        manager.disconnect(user_id, websocket)



@router.websocket("/ws/family-jar/{family_id}")
async def family_jar_ws(websocket: WebSocket, family_id: int, token: str = Query(None)):
    if not token:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        user = get_user_from_token(token, db)
        if user is None:
            await websocket.close(code=4001, reason="Invalid token")
            return
        member = get_member(db, family_id, user.id)
        if not member:
            await websocket.close(code=4403, reason="Family membership required")
            return
    except Exception:
        await websocket.close(code=4403, reason="Family membership required")
        return
    finally:
        db.close()

    if not await manager.connect_family(family_id, websocket):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning(
            "ws family loop error for family %s", family_id, exc_info=True
        )
    finally:
        manager.disconnect_family(family_id, websocket)


