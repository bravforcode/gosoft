from __future__ import annotations

import asyncio
import json
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger("cache.redis")


class RedisClient:
    def __init__(self) -> None:
        self._client: Redis | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> Redis:
        if self._client:
            return self._client
        async with self._lock:
            if self._client:
                return self._client
            settings = get_settings()
            self._client = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                retry_on_timeout=False,
            )
            await self._client.ping()
            logger.info("redis_connected", url=settings.REDIS_URL)
            return self._client

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> str | None:
        client = await self.connect()
        return await client.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        client = await self.connect()
        await client.set(key, value, ex=ttl)

    async def get_json(self, key: str) -> Any | None:
        raw = await self.get(key)
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self.set(key, json.dumps(value, default=str), ttl)

    async def delete(self, key: str) -> None:
        client = await self.connect()
        await client.delete(key)

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        try:
            client = await self.connect()
            await client.publish(channel, json.dumps(payload, default=str))
        except Exception as exc:
            logger.warning("redis_publish_failed", channel=channel, error=str(exc))

    async def pubsub(self) -> PubSub:
        client = await self.connect()
        return client.pubsub()

    async def incr_with_expiry(self, key: str, ttl_seconds: int) -> int:
        client = await self.connect()
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            count, _ = await pipe.execute()
        return int(count)


redis_client = RedisClient()
