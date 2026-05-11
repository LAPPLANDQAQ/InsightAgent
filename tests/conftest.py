"""Shared pytest fixtures."""

from types import SimpleNamespace

import pytest

from app.agents.analyst import Analyst
from app.agents.critic import Critic
from app.agents.planner import Planner
from app.agents.researcher import Researcher
from app.agents.writer import Writer
from app.config import Settings
from app.infra.cache.memory_cache import MemoryCache
from app.infra.search.service import SearchService
from app.tools.extraction_tool import ExtractionTool
from app.tools.search_tool import SearchTool
from app.tools.source_classifier_tool import SourceClassifierTool
from app.tools.sufficiency_tool import SufficiencyTool
from app.tools.webpage_tool import WebpageTool


@pytest.fixture
def fake_llm():
    from tests.fixtures.fake_llm import FakeLLMClient

    return FakeLLMClient()


@pytest.fixture
def stub_search():
    from tests.fixtures.stub_search import StubSearchProvider

    return StubSearchProvider()


@pytest.fixture
def stub_fetch():
    from tests.fixtures.stub_fetch import StubFetchClient

    return StubFetchClient()


@pytest.fixture
def container_with_stubs(fake_llm, stub_search, stub_fetch):
    """Build a complete offline container for workflow tests."""
    settings = Settings(app_env="test", cache_backend="memory", enable_rag_research=False)
    cache = MemoryCache()
    search_service = SearchService([stub_search], cache)
    search_tool = SearchTool(search_service)
    webpage_tool = WebpageTool(stub_fetch)
    extraction_tool = ExtractionTool(fake_llm)
    classifier_tool = SourceClassifierTool()
    sufficiency_tool = SufficiencyTool()
    return SimpleNamespace(
        settings=settings,
        cache=cache,
        llm=fake_llm,
        search_tool=search_tool,
        webpage_tool=webpage_tool,
        extraction_tool=extraction_tool,
        classifier_tool=classifier_tool,
        sufficiency_tool=sufficiency_tool,
        planner=Planner(fake_llm),
        researcher=Researcher(
            search_tool,
            webpage_tool,
            extraction_tool,
            classifier_tool,
            sufficiency_tool,
        ),
        analyst=Analyst(fake_llm),
        writer=Writer(fake_llm),
        critic=Critic(fake_llm, False),
    )
