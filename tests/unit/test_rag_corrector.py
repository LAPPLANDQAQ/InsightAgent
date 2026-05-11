"""Tests for RAGCorrector."""

import pytest

from app.agents.rag_corrector import RAGCorrector
from app.rag.schemas import ChildChunk, RetrievedChunk


@pytest.mark.asyncio
async def test_rag_corrector_emits_issue_for_incorrect():
    """RAGCorrector reports incorrect retrieval without looping."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="url",
        text="text",
        chunk_index=0,
    )
    retrieved = RetrievedChunk(chunk=chunk, retriever_name="test", rank=1, score=0.1)

    result = await RAGCorrector(max_repair_attempts=1).run(
        {"user_query": "q", "retrieved_chunks": [retrieved.model_dump()]}
    )

    assert result["rag_metrics"]["retrieval_quality_grade"] == "incorrect"
    assert result["rag_metrics"]["repair_attempts"] == 1
