# app/core/ws_manager.py
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.user_connections: Dict[int, List[WebSocket]] = {}
        self.family_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.user_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int):
        conns = self.user_connections.get(user_id, [])
        for ws in conns:
            try:
                ws.close()
            except:
                pass
        self.user_connections.pop(user_id, None)

    async def send_user_event(self, user_id: int, data: dict):
        conns = self.user_connections.get(user_id, [])
        for ws in conns:
            await ws.send_json(data)

    async def connect_family(self, jar_id: int, websocket: WebSocket):
        await websocket.accept()
        self.family_connections.setdefault(jar_id, []).append(websocket)

    def disconnect_family(self, jar_id: int, websocket: WebSocket):
        if jar_id in self.family_connections and websocket in self.family_connections[jar_id]:
            self.family_connections[jar_id].remove(websocket)

    async def send_family_event(self, jar_id: int, data: dict):
        conns = self.family_connections.get(jar_id, [])
        for ws in conns:
            await ws.send_json(data)

manager = ConnectionManager()