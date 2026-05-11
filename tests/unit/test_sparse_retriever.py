"""Tests for SparseRetriever."""

from app.rag.retrievers.sparse_retriever import SparseRetriever
from app.rag.schemas import ChildChunk


def test_sparse_retriever_exact_phrase_bonus_and_top_k():
    """Sparse retriever returns query-overlap chunks with top_k respected."""
    chunks = [
        ChildChunk(
            chunk_id="a",
            parent_doc_id="p",
            task_id="t",
            source_id="s",
            source_url="u",
            text="Cursor pricing",
            chunk_index=0,
        ),
        ChildChunk(
            chunk_id="b",
            parent_doc_id="p",
            task_id="t",
            source_id="s",
            source_url="u",
            text="Cursor docs",
            chunk_index=1,
        ),
    ]

    results = SparseRetriever(chunks).retrieve("Cursor pricing", top_k=1)
    assert [item.chunk.chunk_id for item in results] == ["a"]
