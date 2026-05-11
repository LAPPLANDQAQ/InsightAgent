"""Research strategy router agent."""

from typing import Any

from app.schemas.research_strategy import ResearchRoute, ResearchStrategy


class ResearchRouter:
    """Choose a safe retrieval strategy for each research TODO."""

    name = "research_router"

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return research strategies for current TODOs."""
        strategies = [
            self.route_todo(todo).model_dump()
            for todo in state.get("research_todos", [])
            if isinstance(todo, dict)
        ]
        return {
            "research_strategies": strategies,
            "current_stage": self.name,
            "issues": [],
        }

    def route_todo(self, todo: dict[str, Any]) -> ResearchStrategy:
        """Create one strategy from TODO fields."""
        text = f"{todo.get('dimension', '')} {todo.get('query', '')}".lower()
        route: ResearchRoute = "default"
        source_types: list[str] = []
        freshness = False
        if any(term in text for term in ("pricing", "price", "plan", "billing", "cost")):
            route = "pricing"
            source_types = ["official"]
        elif any(term in text for term in ("docs", "documentation", "api")):
            route = "docs"
            source_types = ["official", "docs"]
        elif any(term in text for term in ("github", "repo", "integration", "ecosystem")):
            route = "github"
            source_types = ["github", "community"]
        elif any(term in text for term in ("news", "risk", "policy", "security")):
            route = "news"
            source_types = ["media", "official"]
            freshness = True
        return ResearchStrategy(
            todo_id=str(todo.get("todo_id") or "unknown_todo"),
            route=route,
            search_query=str(todo.get("query") or todo.get("title") or "research"),
            preferred_source_types=source_types,
            freshness_required=freshness,
        )
