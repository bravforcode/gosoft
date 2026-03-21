from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.cache.redis_client import redis_client
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger("cache.service")


class CacheService:
    def __init__(self) -> None:
        self._memory_cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_json(self, key: str) -> Any | None:
        try:
            return await redis_client.get_json(key)
        except Exception as exc:
            logger.warning("cache_get_fallback", key=key, error=str(exc))
            return self._memory_fallback_get(key)

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl or get_settings().REDIS_CACHE_TTL
        try:
            await redis_client.set_json(key, value, ttl)
            return
        except Exception as exc:
            logger.warning("cache_set_fallback", key=key, error=str(exc))
            self._memory_fallback_set(key, value, ttl)

    async def delete(self, key: str) -> None:
        try:
            await redis_client.delete(key)
        except Exception:
            self._memory_cache.pop(key, None)

    async def get_or_set(
        self,
        key: str,
        producer: Callable[[], Awaitable[Any]],
        ttl: int | None = None,
    ) -> Any:
        cached = await self.get_json(key)
        if cached is not None:
            return cached
        async with self._lock:
            cached = await self.get_json(key)
            if cached is not None:
                return cached
            value = await producer()
            await self.set_json(key, value, ttl)
            return value

    def _memory_fallback_get(self, key: str) -> Any | None:
        import time

        item = self._memory_cache.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._memory_cache.pop(key, None)
            return None
        return value

    def _memory_fallback_set(self, key: str, value: Any, ttl: int) -> None:
        import time

        self._memory_cache[key] = (time.time() + ttl, value)


cache_service = CacheService()
