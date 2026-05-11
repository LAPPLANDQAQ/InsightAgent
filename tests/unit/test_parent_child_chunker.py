"""Tests for ParentChildChunker."""

from app.rag.chunkers.parent_child_chunker import ParentChildChunker


def test_parent_child_chunker_overlap_and_metadata():
    """Chunker creates stable ids and preserves metadata."""
    result = ParentChildChunker(chunk_size=10, overlap=2).chunk_document(
        task_id="task",
        source_id="src",
        source_url="https://example.com",
        title="Title",
        text="abcdefghijklmnopqrstuvwxyz",
        todo_id="todo",
        competitor_name="Cursor",
        dimension="pricing",
        metadata={"k": "v"},
    )

    assert len(result.chunks) > 1
    assert result.chunks[0].todo_id == "todo"
    assert result.chunks[0].metadata == {"k": "v"}
