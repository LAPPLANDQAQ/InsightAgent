"""Minimal end-to-end RAG research chain test."""

import json
from pathlib import Path

import pytest

from app.agents.analyst import Analyst
from app.agents.critic import Critic
from app.agents.planner import Planner
from app.agents.rag_indexer import RAGIndexer
from app.agents.rag_researcher import RAGResearcher
from app.agents.research_router import ResearchRouter
from app.agents.task_summarizer import TaskSummarizer
from app.agents.writer import Writer


@pytest.mark.asyncio
async def test_end_to_end_rag_research_chain(fake_llm):
    """Run Planner -> Router -> Indexer -> Researcher -> Summarizer -> Writer."""
    pages = json.loads(Path("tests/fixtures/rag_pages.json").read_text(encoding="utf-8"))
    state = {
        "task_id": "task_e2e_rag",
        "user_query": "AI coding assistants",
        "requested_competitors": ["Cursor", "GitHub Copilot"],
        "requested_dimensions": ["pricing", "features", "ecosystem"],
        "fetched_pages": pages,
    }
    for agent in (
        Planner(fake_llm),
        ResearchRouter(),
        RAGIndexer(),
        RAGResearcher(),
        TaskSummarizer(),
        Analyst(fake_llm),
        Writer(fake_llm),
        Critic(fake_llm, False),
    ):
        state.update(await agent.run(state))

    assert state["research_todos"]
    assert state["rag_chunks"]
    assert state["retrieved_chunks"]
    assert state["competitors"][0]["evidences"]
    assert state["research_notes"]
    assert state["final_report"].strip()
