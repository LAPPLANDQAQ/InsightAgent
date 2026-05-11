"""Integration test for the feature-flagged RAG workflow."""

from types import SimpleNamespace

import pytest

from app.agents.analyst import Analyst
from app.agents.critic import Critic
from app.agents.planner import Planner
from app.agents.rag_indexer import RAGIndexer
from app.agents.rag_researcher import RAGResearcher
from app.agents.research_router import ResearchRouter
from app.agents.task_summarizer import TaskSummarizer
from app.agents.writer import Writer
from app.config import Settings
from app.graph.workflow import build_graph


@pytest.mark.asyncio
async def test_feature_flagged_rag_workflow_runs(fake_llm):
    settings = Settings(app_env="test", cache_backend="memory", enable_rag_research=True)
    container = SimpleNamespace(
        settings=settings,
        planner=Planner(fake_llm),
        research_router=ResearchRouter(),
        rag_indexer=RAGIndexer(),
        rag_researcher=RAGResearcher(),
        task_summarizer=TaskSummarizer(),
        analyst=Analyst(fake_llm),
        writer=Writer(fake_llm),
        critic=Critic(fake_llm, False),
    )

    graph = build_graph(container)
    final = await graph.ainvoke(
        {
            "task_id": "task_rag",
            "user_query": "AI coding assistants",
            "requested_competitors": ["Cursor", "GitHub Copilot"],
            "requested_dimensions": ["pricing", "features", "ecosystem"],
            "fetched_pages": [
                {
                    "source_id": "cursor_pricing",
                    "source_url": "https://cursor.com/pricing",
                    "title": "Cursor Pricing",
                    "text": "Cursor pricing includes a Pro plan for coding teams.",
                    "competitor_name": "Cursor",
                    "dimension": "pricing",
                    "todo_id": "todo_cursor_pricing_1",
                }
            ],
        }
    )

    assert final["task_status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    assert final["research_todos"]
    assert final["rag_chunks"]
    assert final["retrieved_chunks"]
    assert final["research_notes"]
    assert final["final_report"].strip()
