"""Offline workflow integration tests."""

import pytest

from app.graph.workflow import build_graph


@pytest.mark.asyncio
async def test_workflow_runs_with_stub_container(container_with_stubs):
    """Run the full workflow with local test doubles."""
    graph = build_graph(container_with_stubs)
    final = await graph.ainvoke(
        {
            "task_id": "task_integration",
            "user_query": "AI coding assistant market",
            "requested_competitors": ["Cursor", "GitHub Copilot"],
            "requested_dimensions": ["pricing", "features", "ecosystem"],
            "sufficiency_threshold": 0.6,
        }
    )
    assert final["final_report"].strip()
    assert len(final["competitors"]) == 2
    assert final["task_status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    assert final["analysis"]["dimension_analysis"]
