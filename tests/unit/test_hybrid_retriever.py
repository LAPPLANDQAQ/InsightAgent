"""Tests for HybridRetriever."""

from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.schemas import ChildChunk


def test_hybrid_retriever_returns_empty_for_empty_chunks():
    """Hybrid retriever handles empty chunk lists safely."""
    assert HybridRetriever([]).retrieve("query") == []


def test_hybrid_retriever_fuses_sparse_and_dense_results():
    """Hybrid retriever returns fused ranked results."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="url",
        text="Cursor pricing",
        chunk_index=0,
    )

    assert HybridRetriever([chunk]).retrieve("Cursor pricing")[0].rank == 1
