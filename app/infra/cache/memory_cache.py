"""In-memory cache backend."""

import asyncio
import time


class MemoryCache:
    """Process-local TTL cache for tests and lightweight runtime use."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[bytes, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> bytes | None:
        """Get a cached value.

        Args:
            key: Cache key.

        Returns:
            Cached bytes, or None when missing or expired.
        """
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at <= time.time():
                self._items.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: bytes, ttl: int = 21600) -> None:
        """Store a cached value.

        Args:
            key: Cache key.
            value: Serialized value bytes.
            ttl: Time to live in seconds.
        """
        async with self._lock:
            self._items[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        """Delete a cached value.

        Args:
            key: Cache key.
        """
        async with self._lock:
            self._items.pop(key, None)
