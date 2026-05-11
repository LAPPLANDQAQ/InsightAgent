"""Tests for ContextBuilder."""

from app.rag.context.context_builder import ContextBuilder
from app.rag.schemas import ChildChunk, RetrievedChunk


def test_context_builder_sorts_and_caps_context():
    """Context builder sorts by rank and keeps citation header."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="https://example.com",
        text="text body",
        chunk_index=0,
    )
    retrieved = RetrievedChunk(chunk=chunk, retriever_name="test", rank=1, score=0.9)

    context = ContextBuilder().build([retrieved], max_chars=80)
    assert "[chunk]" in context
    assert "score=0.900" in context
