"""Tests for Reciprocal Rank Fusion."""

from app.rag.fusion.rrf import reciprocal_rank_fusion
from app.rag.schemas import ChildChunk, RetrievedChunk


def test_rrf_dedupes_by_chunk_id_and_reassigns_rank():
    """RRF fuses duplicate chunks and preserves retriever scores in metadata."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="url",
        text="text",
        chunk_index=0,
    )
    left = RetrievedChunk(chunk=chunk, retriever_name="sparse", rank=1, score=2.0)
    right = RetrievedChunk(chunk=chunk, retriever_name="dense", rank=2, score=0.5)

    fused = reciprocal_rank_fusion([[left], [right]])
    assert len(fused) == 1
    assert fused[0].rank == 1
    assert fused[0].metadata["sparse_score"] == 2.0
