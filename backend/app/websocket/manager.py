from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket

from app.cache.redis_client import redis_client
from app.core.logging import get_logger
from app.core.security import decode_token
from app.websocket.events import SIVEvent


logger = get_logger("websocket.manager")


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = defaultdict(set)
        self._redis_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._stats_provider: Callable[[], Awaitable[dict[str, Any]]] | None = None
        self.session_id = "server-session"

    async def connect(self, websocket: WebSocket, client_id: str, token: str) -> bool:
        decode_token(token, expected_type="access")
        await websocket.accept()
        self.connections[client_id] = websocket
        self.subscriptions.setdefault(client_id, set())
        logger.info("ws_connected", client_id=client_id)
        return True

    async def disconnect(self, client_id: str) -> None:
        websocket = self.connections.pop(client_id, None)
        self.subscriptions.pop(client_id, None)
        if websocket:
            try:
                await websocket.close()
            except Exception:
                pass
        logger.info("ws_disconnected", client_id=client_id)

    async def broadcast(self, event: SIVEvent) -> None:
        payload = event.model_dump(mode="json")
        stale_clients: list[str] = []
        for client_id, websocket in self.connections.items():
            subscriptions = self.subscriptions.get(client_id) or set()
            if subscriptions and event.type not in subscriptions:
                continue
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                logger.warning("ws_send_failed", client_id=client_id, error=str(exc))
                stale_clients.append(client_id)
        for client_id in stale_clients:
            await self.disconnect(client_id)

    async def send_personal(self, client_id: str, message: dict[str, Any]) -> None:
        websocket = self.connections.get(client_id)
        if websocket:
            await websocket.send_json(message)

    async def subscribe(self, client_id: str, event_types: set[str]) -> None:
        self.subscriptions[client_id] = event_types

    async def start(self, stats_provider: Callable[[], Awaitable[dict[str, Any]]] | None = None) -> None:
        if self._redis_task:
            return
        self._stats_provider = stats_provider
        self._redis_task = asyncio.create_task(self._listen_to_redis())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        for task in (self._redis_task, self._heartbeat_task):
            if task:
                task.cancel()
        self._redis_task = None
        self._heartbeat_task = None

    async def broadcast_heartbeat(self) -> None:
        stats = await self._stats_provider() if self._stats_provider else {}
        event = SIVEvent(type="heartbeat", data=stats, session_id=self.session_id)
        await self.broadcast(event)

    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                await self.broadcast_heartbeat()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("heartbeat_failed", error=str(exc))
            await asyncio.sleep(5)

    async def _listen_to_redis(self) -> None:
        pubsub = await redis_client.pubsub()
        await pubsub.subscribe("siv:events")
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if not data:
                    continue
                payload = json.loads(data)
                event = SIVEvent.model_validate(payload)
                await self.broadcast(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("redis_listener_failed", error=str(exc))
        finally:
            await pubsub.unsubscribe("siv:events")
            await pubsub.close()


websocket_manager = ConnectionManager()
