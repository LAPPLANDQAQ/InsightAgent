"""SQLite-backed parent document and child chunk store."""

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from app.rag.schemas import ChildChunk, ParentDocument


class SQLiteChunkStore:
    """Small sqlite3 store for RAG parent documents and child chunks."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._init_schema()

    def upsert_parent(self, parent: ParentDocument) -> None:
        """Insert or replace a parent document."""
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into parents(parent_doc_id, payload)
                values (?, ?)
                """,
                (parent.parent_doc_id, parent.model_dump_json()),
            )

    def upsert_chunks(self, chunks: Iterable[ChildChunk]) -> None:
        """Insert or replace child chunks."""
        with self._connect() as conn:
            conn.executemany(
                "insert or replace into chunks(chunk_id, parent_doc_id, payload) values (?, ?, ?)",
                [
                    (chunk.chunk_id, chunk.parent_doc_id, chunk.model_dump_json())
                    for chunk in chunks
                ],
            )

    def list_chunks(self, task_id: str | None = None) -> list[ChildChunk]:
        """Return stored chunks, optionally filtered by task id."""
        with self._connect() as conn:
            rows = conn.execute("select payload from chunks order by chunk_id").fetchall()
        chunks = [ChildChunk.model_validate(json.loads(row[0])) for row in rows]
        if task_id is None:
            return chunks
        return [chunk for chunk in chunks if chunk.task_id == task_id]

    def get_parent(self, parent_doc_id: str) -> ParentDocument | None:
        """Return a parent document by id."""
        with self._connect() as conn:
            row = conn.execute(
                "select payload from parents where parent_doc_id = ?",
                (parent_doc_id,),
            ).fetchone()
        if row is None:
            return None
        return ParentDocument.model_validate(json.loads(row[0]))

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "create table if not exists parents(parent_doc_id text primary key, payload text)"
            )
            conn.execute(
                """
                create table if not exists chunks(
                    chunk_id text primary key,
                    parent_doc_id text not null,
                    payload text not null
                )
                """
            )
