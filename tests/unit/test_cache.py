"""Cache backend tests."""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from app.infra.cache.memory_cache import MemoryCache
from app.infra.cache.sqlite_cache import SQLiteCache


def _db_path() -> Path:
    path = Path("data") / f"unit-cache-{uuid4().hex}.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@pytest.mark.asyncio
async def test_memory_cache_get_set_delete():
    cache = MemoryCache()
    await cache.set("k", b"value")
    assert await cache.get("k") == b"value"
    await cache.delete("k")
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_memory_cache_expires():
    cache = MemoryCache()
    await cache.set("k", b"value", ttl=0)
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_sqlite_cache_get_set_delete():
    db_path = _db_path()
    cache = SQLiteCache(db_path)
    await cache.set("k", b"value")
    assert await cache.get("k") == b"value"
    await cache.delete("k")
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_sqlite_cache_expires():
    db_path = _db_path()
    cache = SQLiteCache(db_path)
    await cache.set("k", b"value", ttl=0)
    await asyncio.sleep(0)
    assert await cache.get("k") is None
