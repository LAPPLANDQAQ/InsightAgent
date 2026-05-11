"""Tests for Planner TODO generation."""

import pytest

from app.agents.planner import Planner
from app.schemas.plan import ResearchPlan


def test_fallback_todos_cover_competitors_and_dimensions():
    plan = ResearchPlan(
        market="AI coding",
        competitors=["Cursor", "GitHub Copilot"],
        dimensions=["pricing", "features", "ecosystem"],
        search_queries={},
        required_fields={
            "pricing": ["claim"],
            "features": ["claim"],
            "ecosystem": ["claim"],
        },
    )

    filled = Planner._ensure_research_todos(plan, task_id="task_1")

    assert len(filled.research_todos) == 6
    assert filled.research_todos[0].todo_id == "todo_cursor_pricing_1"
    assert filled.research_todos[0].competitor_name == "Cursor"
    assert filled.research_todos[0].dimension == "pricing"


@pytest.mark.asyncio
async def test_planner_populates_todos_with_fallback(fake_llm):
    planner = Planner(fake_llm)

    result = await planner.run(
        {
            "task_id": "task_1",
            "user_query": "AI coding",
            "requested_competitors": ["Cursor", "GitHub Copilot"],
            "requested_dimensions": ["pricing", "features", "ecosystem"],
        }
    )

    assert result["research_todos"]
    assert result["plan"]["research_todos"]
