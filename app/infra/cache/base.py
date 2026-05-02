"""Cache backend protocol."""

from typing import Protocol


class CacheBackend(Protocol):
    """Key-value cache interface for serialized bytes."""

    async def get(self, key: str) -> bytes | None:
        """Get a cached value.

        Args:
            key: Cache key.

        Returns:
            Cached bytes, or None when the key is absent.
        """
        ...

    async def set(self, key: str, value: bytes, ttl: int = 21600) -> None:
        """Store a cached value.

        Args:
            key: Cache key.
            value: Serialized bytes to store.
            ttl: Time to live in seconds.
        """
        ...

    async def delete(self, key: str) -> None:
        """Delete a cached value.

        Args:
            key: Cache key to remove.
        """
        ...
