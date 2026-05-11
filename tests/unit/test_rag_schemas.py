"""Tests for RAG schemas."""

import pytest
from pydantic import ValidationError

from app.rag.schemas import ChildChunk, ParentDocument, RetrievedChunk


def test_rag_schema_defaults_and_bounds():
    """RAG schemas validate ranks, chunk indexes, and default metadata."""
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
        parent_doc_id=parent.parent_doc_id,
        task_id="task",
        source_id="src",
        source_url="https://example.com",
        text="text",
        chunk_index=0,
    )
    retrieved = RetrievedChunk(chunk=chunk, retriever_name="test", rank=1, score=0.5)

    assert parent.metadata == {}
    assert chunk.metadata == {}
    assert retrieved.rank == 1
    with pytest.raises(ValidationError):
        ChildChunk(
            chunk_id="bad",
            parent_doc_id="parent",
            task_id="task",
            source_id="src",
            source_url="url",
            text="text",
            chunk_index=-1,
        )
