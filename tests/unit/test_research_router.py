"""Tests for ResearchRouter."""

import pytest

from app.agents.research_router import ResearchRouter


@pytest.mark.asyncio
async def test_research_router_outputs_strategies():
    """ResearchRouter routes pricing/docs/github/news/default TODOs."""
    todos = [
        {"todo_id": "pricing", "dimension": "pricing", "query": "pricing"},
        {"todo_id": "docs", "dimension": "docs", "query": "api docs"},
        {"todo_id": "github", "dimension": "ecosystem", "query": "github repo"},
        {"todo_id": "news", "dimension": "risk", "query": "security news"},
        {"todo_id": "default", "dimension": "other", "query": "other"},
    ]

    result = await ResearchRouter().run({"research_todos": todos})
    routes = [item["route"] for item in result["research_strategies"]]
    assert routes == ["pricing", "docs", "github", "news", "default"]
