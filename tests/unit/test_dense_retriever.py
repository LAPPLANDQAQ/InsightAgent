"""Tests for DenseRetriever."""

from app.rag.index.embedding_client import DeterministicEmbeddingClient
from app.rag.retrievers.dense_retriever import DenseRetriever
from app.rag.schemas import ChildChunk


def test_dense_retriever_uses_deterministic_embeddings():
    """Dense retriever returns deterministic cosine matches."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="url",
        text="Cursor pricing",
        chunk_index=0,
    )

    results = DenseRetriever([chunk], DeterministicEmbeddingClient()).retrieve("pricing")
    assert results[0].chunk.chunk_id == "chunk"
