"""Dependency injection container."""

from app.agents.analyst import Analyst
from app.agents.critic import Critic
from app.agents.planner import Planner
from app.agents.researcher import Researcher
from app.agents.writer import Writer
from app.config import Settings
from app.infra.cache.memory_cache import MemoryCache
from app.infra.cache.sqlite_cache import SQLiteCache
from app.infra.fetch.httpx_client import HttpxFetchClient
from app.infra.llm.qwen_dashscope_client import QwenDashScopeClient
from app.infra.search.base import SearchProvider
from app.infra.search.duckduckgo import DuckDuckGoProvider
from app.infra.search.service import SearchService
from app.infra.search.tavily import TavilyProvider
from app.tools.extraction_tool import ExtractionTool
from app.tools.search_tool import SearchTool
from app.tools.source_classifier_tool import SourceClassifierTool
from app.tools.sufficiency_tool import SufficiencyTool
from app.tools.webpage_tool import WebpageTool


class Container:
    """Runtime dependency container."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = SQLiteCache() if settings.cache_backend == "sqlite" else MemoryCache()
        self.llm = QwenDashScopeClient(
            api_key=settings.dashscope_api_key,
            base_url=settings.llm_base_url,
            heavy_model=settings.llm_heavy_model,
            light_model=settings.llm_light_model,
            fallback_model=settings.llm_fallback_model,
        )
        self.search_service = SearchService(
            self._search_providers(),
            self.cache,
            settings.max_concurrent_search,
        )
        self.fetch_client = HttpxFetchClient(self.cache)
        self.search_tool = SearchTool(self.search_service)
        self.webpage_tool = WebpageTool(self.fetch_client)
        self.extraction_tool = ExtractionTool(self.llm, self.cache)
        self.classifier_tool = SourceClassifierTool()
        self.sufficiency_tool = SufficiencyTool()
        self.planner = Planner(self.llm)
        self.researcher = Researcher(
            self.search_tool,
            self.webpage_tool,
            self.extraction_tool,
            self.classifier_tool,
            self.sufficiency_tool,
            threshold=settings.sufficiency_threshold,
            max_rounds=settings.max_search_rounds_per_competitor,
        )
        self.analyst = Analyst(self.llm)
        self.writer = Writer(self.llm)
        self.critic = Critic(self.llm, settings.enable_llm_critic)

    def _search_providers(self) -> list[SearchProvider]:
        providers: list[SearchProvider] = []
        for name in self.settings.search_providers.split(","):
            normalized = name.strip().lower()
            if normalized == "tavily" and self.settings.tavily_api_key:
                providers.append(TavilyProvider(api_key=self.settings.tavily_api_key))
            elif normalized == "duckduckgo":
                providers.append(DuckDuckGoProvider())
        if not providers:
            providers.append(DuckDuckGoProvider())
        return providers
