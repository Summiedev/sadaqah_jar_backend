# app/core/ws_manager.py
import asyncio
import json
import logging
import threading
from uuid import uuid4
from typing import Dict, List, Optional
from fastapi import WebSocket
import redis

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

# Hard cap on sockets a single user (or family room) may hold open at once.
# Without this, one client can open unlimited connections and exhaust server
# memory / file descriptors, and every broadcast fans out to all of them.
MAX_CONNECTIONS_PER_KEY = 5
WS_EVENTS_CHANNEL = "mizan:ws:events"


class ConnectionManager:
    def __init__(self):
        self.user_connections: Dict[int, List[WebSocket]] = {}
        self.family_connections: Dict[int, List[WebSocket]] = {}
        # The main asyncio loop, captured at app startup so sync (threadpool)
        # request handlers can schedule websocket sends without awaiting.
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._instance_id = uuid4().hex
        self._listener_thread: Optional[threading.Thread] = None
        self._listener_stop = threading.Event()

    def bind_loop(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Capture the running event loop. Call once during app startup."""
        try:
            self._loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def start_pubsub_listener(self) -> None:
        if self._listener_thread and self._listener_thread.is_alive():
            return
        self._listener_stop.clear()
        self._listener_thread = threading.Thread(
            target=self._listen_for_remote_events,
            name="ws-redis-pubsub",
            daemon=True,
        )
        self._listener_thread.start()

    def stop_pubsub_listener(self) -> None:
        self._listener_stop.set()

    def _publish_remote_event(self, scope: str, key: int, data: dict) -> None:
        try:
            redis_client.publish(
                WS_EVENTS_CHANNEL,
                json.dumps(
                    {
                        "source": self._instance_id,
                        "scope": scope,
                        "key": key,
                        "data": data,
                    }
                ),
            )
        except redis.RedisError as exc:
            logger.warning("ws redis publish failed; local delivery only: %s", exc)

    def _listen_for_remote_events(self) -> None:
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        try:
            pubsub.subscribe(WS_EVENTS_CHANNEL)
            for message in pubsub.listen():
                if self._listener_stop.is_set():
                    break
                try:
                    payload = json.loads(message["data"])
                    if payload.get("source") == self._instance_id:
                        continue
                    scope = payload.get("scope")
                    key = int(payload.get("key"))
                    data = payload.get("data") or {}
                    loop = self._loop
                    if loop is None or loop.is_closed():
                        continue
                    if scope == "user":
                        asyncio.run_coroutine_threadsafe(
                            self.send_user_event(key, data, publish=False), loop
                        )
                    elif scope == "family":
                        asyncio.run_coroutine_threadsafe(
                            self.send_family_event(key, data, publish=False), loop
                        )
                except Exception:
                    logger.debug("Invalid ws pubsub message", exc_info=True)
        except redis.RedisError as exc:
            logger.warning("ws redis listener stopped: %s", exc)
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

    def send_user_event_threadsafe(self, user_id: int, data: dict) -> None:
        """Schedule a user event from a synchronous (threadpool) context.

        Safe to call from a sync route handler running on Starlette's
        threadpool. Never raises into the caller; failures are logged.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning("ws loop unavailable; dropping user event for %s", user_id)
            return
        try:
            asyncio.run_coroutine_threadsafe(self.send_user_event(user_id, data), loop)
        except Exception:
            logger.exception("Failed to schedule user event for %s", user_id)

    def send_family_event_threadsafe(self, family_id: int, data: dict) -> None:
        """Schedule a family event from a synchronous (threadpool) context."""
        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning(
                "ws loop unavailable; dropping family event for %s", family_id
            )
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.send_family_event(family_id, data), loop
            )
        except Exception:
            logger.exception("Failed to schedule family event for %s", family_id)

    async def connect(self, user_id: int, websocket: WebSocket) -> bool:
        """Accept and register a user socket.

        Returns False (and closes the socket) if the user is already at the
        per-user connection cap, so a single client cannot open unbounded
        sockets.
        """
        conns = self.user_connections.get(user_id, [])
        if len(conns) >= MAX_CONNECTIONS_PER_KEY:
            logger.warning(
                "User %s exceeded max ws connections (%s); rejecting",
                user_id,
                MAX_CONNECTIONS_PER_KEY,
            )
            await websocket.close(code=4429)
            return False
        await websocket.accept()
        self.user_connections.setdefault(user_id, []).append(websocket)
        return True

    def disconnect(self, user_id: int, websocket: WebSocket):
        conns = self.user_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.user_connections.pop(user_id, None)

    async def send_user_event(self, user_id: int, data: dict, *, publish: bool = True):
        if publish:
            self._publish_remote_event("user", user_id, data)
        await self._broadcast(self.user_connections, user_id, data)

    async def connect_family(self, jar_id: int, websocket: WebSocket) -> bool:
        conns = self.family_connections.get(jar_id, [])
        if len(conns) >= MAX_CONNECTIONS_PER_KEY:
            logger.warning(
                "Family %s exceeded max ws connections (%s); rejecting",
                jar_id,
                MAX_CONNECTIONS_PER_KEY,
            )
            await websocket.close(code=4429)
            return False
        await websocket.accept()
        self.family_connections.setdefault(jar_id, []).append(websocket)
        return True

    def disconnect_family(self, jar_id: int, websocket: WebSocket):
        conns = self.family_connections.get(jar_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.family_connections.pop(jar_id, None)

    async def send_family_event(self, jar_id: int, data: dict, *, publish: bool = True):
        if publish:
            self._publish_remote_event("family", jar_id, data)
        await self._broadcast(self.family_connections, jar_id, data)

    async def _broadcast(
        self, registry: Dict[int, List[WebSocket]], key: int, data: dict
    ) -> None:
        """Fan out ``data`` to every socket for ``key``, isolating failures.

        A dead/broken socket must NOT abort delivery to the other sockets in
        the same room, and must be pruned so it can't leak or be retried
        forever. Each send is wrapped independently; failed sockets are
        removed after the fan-out.
        """
        # Iterate a snapshot so concurrent disconnects can't mutate the list
        # mid-iteration.
        conns = list(registry.get(key, []))
        if not conns:
            return
        dead: List[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                logger.debug("Pruning dead ws for key %s", key, exc_info=True)
                dead.append(ws)
        if dead:
            live = registry.get(key, [])
            for ws in dead:
                if ws in live:
                    live.remove(ws)
            if not live:
                registry.pop(key, None)


manager = ConnectionManager()
