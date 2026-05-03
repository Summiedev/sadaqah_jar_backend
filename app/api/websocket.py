from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from app.core.ws_manager import manager
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from app.models.user import User

router = APIRouter(prefix="/websock", tags=["websocket"])

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
    user = get_user_from_token(token, db)
    if user is None or user.id != user_id:
        await websocket.close(code=4001)
        db.close()
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    finally:
        db.close()

@router.websocket("/ws/family-jar/{jar_id}")
async def family_jar_ws(websocket: WebSocket, jar_id: int, token: str = Query(None)):
    if not token:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    user = get_user_from_token(token, db)
    if user is None:
        await websocket.close(code=4001)
        db.close()
        return

    await manager.connect_family(jar_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_family(jar_id, websocket)
    finally:
        db.close()