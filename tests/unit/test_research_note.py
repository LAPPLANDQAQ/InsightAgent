"""Tests for ResearchNote schema."""

import pytest
from pydantic import ValidationError

from app.schemas.research_note import ResearchNote


def _note(**overrides):
    data = {
        "note_id": "note_1",
        "task_id": "task_1",
        "todo_id": "todo_1",
        "competitor_name": "Cursor",
        "dimension": "pricing",
        "summary": "Summary",
        "confidence": 0.7,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    data.update(overrides)
    return ResearchNote(**data)


def test_research_note_defaults():
    note = _note()

    assert note.evidence_ids == []
    assert note.chunk_ids == []
    assert note.source_urls == []


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_research_note_confidence_bounds(confidence):
    with pytest.raises(ValidationError):
        _note(confidence=confidence)


def test_research_note_rejects_empty_summary():
    with pytest.raises(ValidationError):
        _note(summary="")
