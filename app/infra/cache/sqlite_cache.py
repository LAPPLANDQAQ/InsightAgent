"""SQLite cache backend."""

import asyncio
import sqlite3
import time
from pathlib import Path


class SQLiteCache:
    """SQLite-backed TTL cache."""

    def __init__(self, db_path: str | Path = "data/cache.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON cache_entries(expires_at)"
            )
            conn.commit()

    async def get(self, key: str) -> bytes | None:
        """Get a cached value.

        Args:
            key: Cache key.

        Returns:
            Cached bytes, or None when missing or expired.
        """
        async with self._lock:
            now = time.time()
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    return None
                value, expires_at = row
                if expires_at <= now:
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    conn.commit()
                    return None
                return bytes(value)

    async def set(self, key: str, value: bytes, ttl: int = 21600) -> None:
        """Store a cached value.

        Args:
            key: Cache key.
            value: Serialized value bytes.
            ttl: Time to live in seconds.
        """
        async with self._lock:
            now = time.time()
            expires_at = now + ttl
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO cache_entries(key, value, expires_at, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at,
                        created_at = excluded.created_at
                    """,
                    (key, value, expires_at, now),
                )
                conn.commit()

    async def delete(self, key: str) -> None:
        """Delete a cached value.

        Args:
            key: Cache key.
        """
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
