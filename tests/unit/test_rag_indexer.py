"""Tests for RAGIndexer."""

import pytest

from app.agents.rag_indexer import RAGIndexer


@pytest.mark.asyncio
async def test_rag_indexer_consumes_existing_text_and_reports_empty():
    """RAGIndexer indexes provided state text without fetching pages."""
    result = await RAGIndexer(chunk_size=20, overlap=2).run(
        {
            "task_id": "task",
            "fetched_pages": [
                {
                    "source_id": "src",
                    "source_url": "https://example.com",
                    "text": "Cursor pricing has plans.",
                },
                {"source_id": "empty", "source_url": "https://example.com", "text": ""},
            ],
        }
    )

    assert result["rag_parent_docs"]
    assert result["rag_chunks"]
    assert result["issues"] == ["rag_index_empty:empty"]
