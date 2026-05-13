"""Tests for workflow state merging."""

from app.graph.reducers import (
    check_sufficiency,
    merge_state,
    route_after_critic,
    route_after_sufficiency,
)


def test_merge_state_appends_lists_and_overrides_contract_fields():
    merged = merge_state(
        {
            "issues": ["old"],
            "research_notes": [{"note_id": "old"}],
            "retrieved_chunks": [{"chunk_id": "old"}],
            "research_todos": [{"todo_id": "old"}],
            "rag_metrics": {"old": 1},
            "agent_metrics": {"planner": {"old": 1}},
            "harness_metrics": {"tool_calls": 1},
        },
        {
            "issues": ["new"],
            "research_notes": [{"note_id": "new"}],
            "retrieved_chunks": [{"chunk_id": "new"}],
            "research_todos": [{"todo_id": "new"}],
            "rag_metrics": {"new": 2},
            "agent_metrics": {"writer": {"new": 2}},
            "harness_metrics": {"tool_calls": 2},
        },
    )

    assert merged["issues"] == ["old", "new"]
    assert [item["note_id"] for item in merged["research_notes"]] == ["old", "new"]
    assert [item["chunk_id"] for item in merged["retrieved_chunks"]] == ["old", "new"]
    assert merged["research_todos"] == [{"todo_id": "new"}]
    assert merged["rag_metrics"] == {"new": 2}
    assert merged["agent_metrics"] == {"writer": {"new": 2}}
    assert merged["harness_metrics"] == {"tool_calls": 2}


def test_merge_state_appends_when_only_one_side_has_append_field():
    merged = merge_state({"issues": ["old"]}, {"current_stage": "writer"})

    assert merged["issues"] == ["old"]


def test_merge_state_dedupes_issues_but_not_research_notes_or_chunks():
    merged = merge_state(
        {
            "issues": ["old", "dupe"],
            "research_notes": [{"note_id": "same"}],
            "retrieved_chunks": [{"chunk_id": "same"}],
        },
        {
            "issues": ["dupe", "new", "old"],
            "research_notes": [{"note_id": "same"}],
            "retrieved_chunks": [{"chunk_id": "same"}],
        },
    )

    assert merged["issues"] == ["old", "dupe", "new"]
    assert [item["note_id"] for item in merged["research_notes"]] == ["same", "same"]
    assert [item["chunk_id"] for item in merged["retrieved_chunks"]] == ["same", "same"]


def test_check_sufficiency_increments_global_loop_count():
    update = check_sufficiency({"iteration_count": 1, "workflow_loop_count": 2})

    assert update["iteration_count"] == 2
    assert update["workflow_loop_count"] == 3


def test_critic_route_finalizes_when_global_loop_guard_exceeded():
    route = route_after_critic(
        {
            "critic_issues": [{"target_stage": "writer"}],
            "critic_rounds": 0,
            "max_iterations": 2,
            "workflow_loop_count": 4,
        }
    )

    assert route == "finalize"


def test_critic_route_still_routes_below_global_loop_guard():
    route = route_after_critic(
        {
            "critic_issues": [{"target_stage": "writer"}],
            "critic_rounds": 0,
            "max_iterations": 2,
            "workflow_loop_count": 3,
        }
    )

    assert route == "writer"


def test_sufficiency_route_still_uses_threshold_result():
    assert route_after_sufficiency(
        {
            "sufficiency": {"is_sufficient": True},
            "iteration_count": 99,
            "max_iterations": 1,
        }
    ) == "analyst"
