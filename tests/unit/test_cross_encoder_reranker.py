"""Tests for optional rerankers."""

from app.rag.rerankers.cross_encoder_reranker import CrossEncoderReranker
from app.rag.rerankers.fake_reranker import FakeReranker
from app.rag.schemas import ChildChunk, RetrievedChunk


def test_cross_encoder_constructs_without_loading_and_fake_scores():
    """CrossEncoderReranker degrades safely and FakeReranker assigns scores."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="url",
        text="Cursor pricing",
        chunk_index=0,
    )
    candidate = RetrievedChunk(chunk=chunk, retriever_name="rrf", rank=1, score=0.1)

    assert CrossEncoderReranker().rerank("query", [candidate], top_n=1)
    assert FakeReranker().rerank("Cursor pricing", [candidate])[0].rerank_score is not None
