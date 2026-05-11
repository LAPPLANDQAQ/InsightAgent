"""Tests for SQLiteChunkStore."""

from app.rag.schemas import ChildChunk, ParentDocument
from app.rag.stores.sqlite_chunk_store import SQLiteChunkStore


def test_sqlite_chunk_store_upserts_without_duplicates(tmp_path):
    """SQLite store upserts parents and chunks."""
    store = SQLiteChunkStore(tmp_path / "chunks.sqlite")
    parent = ParentDocument(
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="https://example.com",
        text="text",
        created_at="2026-01-01T00:00:00+00:00",
    )
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="https://example.com",
        text="text",
        chunk_index=0,
    )

    store.upsert_parent(parent)
    store.upsert_chunks([chunk, chunk])

    assert store.get_parent("parent") == parent
    assert len(store.list_chunks("task")) == 1
