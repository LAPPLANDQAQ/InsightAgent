"""Run a local fake-data RAG research demo."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.rag_indexer import RAGIndexer
from app.agents.rag_researcher import RAGResearcher
from app.agents.research_router import ResearchRouter
from app.agents.task_summarizer import TaskSummarizer
from app.agents.writer import Writer
from app.schemas.research_todo import ResearchTodo


class DemoWriterLLM:
    """Fake writer LLM for the demo."""

    async def invoke(self, **kwargs: object) -> str:
        """Return a deterministic Markdown report."""
        del kwargs
        return "# Demo Report\n\n- Cursor pricing has public evidence [ev_todo_cursor_pricing_1]."


async def main() -> None:
    """Run the demo and print a report."""
    todo = ResearchTodo(
        todo_id="todo_cursor_pricing",
        task_id="demo_task",
        competitor_name="Cursor",
        dimension="pricing",
        title="Research Cursor / pricing",
        intent="Collect pricing evidence.",
        query="Cursor pricing official plan",
        created_at="2026-01-01T00:00:00+00:00",
    )
    state = {
        "task_id": "demo_task",
        "user_query": "AI coding assistants",
        "research_todos": [todo.model_dump()],
        "competitors": [{"name": "Cursor", "sources": [], "evidences": []}],
        "fetched_pages": [
            {
                "source_id": "cursor_pricing",
                "source_url": "https://cursor.com/pricing",
                "title": "Cursor Pricing",
                "text": "Cursor pricing includes Pro and Business plans for coding teams.",
                "competitor_name": "Cursor",
                "dimension": "pricing",
                "todo_id": "todo_cursor_pricing",
            }
        ],
    }
    for agent in (ResearchRouter(), RAGIndexer(), RAGResearcher(), TaskSummarizer()):
        state.update(await agent.run(state))
    report = await Writer(DemoWriterLLM()).run(state)
    print(report["final_report"])


if __name__ == "__main__":
    asyncio.run(main())
