"""Dependency container tests."""

import app.container as container_module
from app.config import Settings
from app.container import Container


def test_container_skips_rag_agents_when_rag_research_disabled():
    container = Container(
        Settings(app_env="test", cache_backend="memory", enable_rag_research=False)
    )

    assert container.rag_indexer is None
    assert container.rag_researcher is None
    assert container.research_router is None
    assert container.task_summarizer is None


def test_container_builds_rag_agents_when_rag_research_enabled():
    container = Container(
        Settings(app_env="test", cache_backend="memory", enable_rag_research=True)
    )

    assert container.rag_indexer is not None
    assert container.rag_researcher is not None
    assert container.research_router is not None
    assert container.task_summarizer is not None


def test_container_passes_llm_concurrency(monkeypatch):
    captured: dict[str, int] = {}

    class FakeDeepSeekClient:
        def __init__(
            self,
            *,
            api_key: str,
            base_url: str,
            heavy_model: str,
            light_model: str,
            fallback_model: str,
            max_concurrent_heavy: int,
            max_concurrent_light: int,
        ) -> None:
            captured["heavy"] = max_concurrent_heavy
            captured["light"] = max_concurrent_light

    monkeypatch.setattr(container_module, "DeepSeekClient", FakeDeepSeekClient)

    Container(
        Settings(
            app_env="test",
            cache_backend="memory",
            enable_rag_research=False,
            max_concurrent_llm_heavy=1,
            max_concurrent_llm_light=3,
        )
    )

    assert captured == {"heavy": 1, "light": 3}
