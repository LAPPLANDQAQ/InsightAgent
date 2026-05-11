"""Tests for workflow state merging."""

from app.graph.reducers import merge_state


def test_merge_state_appends_lists_and_overrides_contract_fields():
    merged = merge_state(
        {
            "issues": ["old"],
            "research_notes": [{"note_id": "old"}],
            "retrieved_chunks": [{"chunk_id": "old"}],
            "research_todos": [{"todo_id": "old"}],
            "rag_metrics": {"old": 1},
        },
        {
            "issues": ["new"],
            "research_notes": [{"note_id": "new"}],
            "retrieved_chunks": [{"chunk_id": "new"}],
            "research_todos": [{"todo_id": "new"}],
            "rag_metrics": {"new": 2},
        },
    )

    assert merged["issues"] == ["old", "new"]
    assert [item["note_id"] for item in merged["research_notes"]] == ["old", "new"]
    assert [item["chunk_id"] for item in merged["retrieved_chunks"]] == ["old", "new"]
    assert merged["research_todos"] == [{"todo_id": "new"}]
    assert merged["rag_metrics"] == {"new": 2}
