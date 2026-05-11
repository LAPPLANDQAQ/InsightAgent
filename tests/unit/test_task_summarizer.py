"""Tests for TaskSummarizer."""

import pytest

from app.agents.task_summarizer import TaskSummarizer


@pytest.mark.asyncio
async def test_task_summarizer_with_evidence():
    state = {
        "task_id": "task_1",
        "research_todos": [
            {
                "todo_id": "todo_1",
                "task_id": "task_1",
                "competitor_name": "Cursor",
                "dimension": "pricing",
            }
        ],
        "competitors": [
            {
                "name": "Cursor",
                "evidences": [
                    {
                        "evidence_id": "ev_1",
                        "todo_id": "todo_1",
                        "source_url": "https://example.com",
                    }
                ],
            }
        ],
    }

    result = await TaskSummarizer().run(state)

    note = result["research_notes"][0]
    assert note["evidence_ids"] == ["ev_1"]
    assert note["confidence"] > 0.5
    assert "research_notes" not in state


@pytest.mark.asyncio
async def test_task_summarizer_without_evidence():
    state = {
        "task_id": "task_1",
        "research_todos": [
            {
                "todo_id": "todo_1",
                "task_id": "task_1",
                "competitor_name": "Cursor",
                "dimension": "pricing",
            }
        ],
        "competitors": [],
    }

    result = await TaskSummarizer().run(state)

    note = result["research_notes"][0]
    assert note["confidence"] <= 0.3
    assert note["limitations"]
