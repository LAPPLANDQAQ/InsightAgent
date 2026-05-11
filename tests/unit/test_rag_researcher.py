"""Tests for RAGResearcher."""

import pytest

from app.agents.rag_researcher import RAGResearcher
from app.rag.schemas import ChildChunk


@pytest.mark.asyncio
async def test_rag_researcher_filters_by_todo_and_emits_evidence():
    """RAGResearcher retrieves scoped chunks and writes evidence to competitors."""
    chunk = ChildChunk(
        chunk_id="chunk",
        parent_doc_id="parent",
        task_id="task",
        todo_id="todo",
        source_id="src",
        source_url="https://example.com",
        competitor_name="Cursor",
        dimension="pricing",
        text="Cursor pricing",
        chunk_index=0,
    )

    result = await RAGResearcher().run(
        {
            "rag_chunks": [chunk.model_dump()],
            "research_todos": [
                {
                    "todo_id": "todo",
                    "competitor_name": "Cursor",
                    "dimension": "pricing",
                    "query": "Cursor pricing",
                }
            ],
            "competitors": [],
        }
    )

    assert result["retrieved_chunks"]
    assert result["competitors"][0]["evidences"][0]["chunk_id"] == "chunk"
