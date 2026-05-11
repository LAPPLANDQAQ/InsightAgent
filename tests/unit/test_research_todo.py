"""Tests for ResearchTodo schema."""

import pytest
from pydantic import ValidationError

from app.schemas.research_todo import ResearchTodo


def _todo(**overrides):
    data = {
        "todo_id": "todo_1",
        "task_id": "task_1",
        "competitor_name": "Cursor",
        "dimension": "pricing",
        "title": "Research Cursor pricing",
        "intent": "Collect pricing evidence.",
        "query": "Cursor pricing",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    data.update(overrides)
    return ResearchTodo(**data)


def test_research_todo_defaults():
    todo = _todo()

    assert todo.status == "pending"
    assert todo.preferred_source_types == []
    assert todo.expected_evidence == []


@pytest.mark.parametrize("field,value", [("priority", 0), ("priority", 6), ("retry_count", -1)])
def test_research_todo_numeric_validation(field, value):
    with pytest.raises(ValidationError):
        _todo(**{field: value})


def test_research_todo_rejects_empty_id():
    with pytest.raises(ValidationError):
        _todo(todo_id="")
