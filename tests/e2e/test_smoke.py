"""Offline end-to-end smoke tests."""

import time

import pytest

from app.graph.workflow import build_graph


@pytest.mark.asyncio
async def test_full_pipeline_with_fixtures(container_with_stubs):
    """Run the user-facing pipeline without external network access."""
    started = time.perf_counter()
    graph = build_graph(container_with_stubs)
    final = await graph.ainvoke(
        {
            "task_id": "task_e2e",
            "user_query": "AI coding assistant market",
            "requested_competitors": [],
            "requested_dimensions": [],
            "sufficiency_threshold": 0.6,
        }
    )
    assert time.perf_counter() - started < 5
    assert final["final_report"].strip()
    assert len(final["competitors"]) >= 2
    assert final["task_status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    for item in final["analysis"]["dimension_analysis"]:
        assert item["evidence_refs"]
