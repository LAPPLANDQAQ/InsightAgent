"""Tests for RetrievalQualityGrader."""

from app.rag.quality.retrieval_quality_grader import RetrievalQualityGrader
from app.rag.schemas import ChildChunk, RetrievedChunk


def _chunk(score: float) -> RetrievedChunk:
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="url",
        text="text",
        chunk_index=0,
    )
    return RetrievedChunk(chunk=chunk, retriever_name="test", rank=1, score=score)


def test_retrieval_quality_thresholds():
    """Retrieval quality thresholds classify correct/ambiguous/incorrect."""
    grader = RetrievalQualityGrader()

    assert grader.grade("q", [_chunk(0.8)]) == "correct"
    assert grader.grade("q", [_chunk(0.4)]) == "ambiguous"
    assert grader.grade("q", [_chunk(0.1)]) == "incorrect"
    assert grader.grade("q", []) == "incorrect"
