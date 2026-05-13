"""Tool layer tests."""

import pytest

from app.infra.cache.memory_cache import MemoryCache
from app.infra.llm.base import ModelRole
from app.infra.search.base import SearchResult
from app.schemas.evidence import EvidenceItem
from app.tools.dedup import dedupe_search_results, normalize_url
from app.tools.extraction_tool import ExtractionTool
from app.tools.search_tool import SearchTool
from app.tools.source_classifier_tool import SourceClassifierTool
from app.tools.sufficiency_tool import SufficiencyTool
from app.tools.webpage_tool import WebpageTool
from tests.fixtures.stub_search import StubSearchProvider


class SearchServiceStub:
    """Small search service stub for SearchTool tests."""

    def __init__(self) -> None:
        self.provider = StubSearchProvider(
            results=[
                SearchResult(
                    title="A",
                    url="https://example.com?utm_source=x",
                    snippet="",
                    provider="s",
                ),
                SearchResult(title="B", url="https://example.com/", snippet="", provider="s"),
            ]
        )

    async def search(self, query: str, max_results: int = 5):
        """Delegate to the stub provider."""
        return await self.provider.search(query, max_results)


class RecordingLLM:
    """LLM stub that records full prompts for extraction tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def invoke(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        schema=None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 30.0,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "model_role": model_role,
                "schema": schema.__name__ if schema else None,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout": timeout,
            }
        )
        assert schema is not None
        return schema.model_validate({"evidences": [_evidence().model_dump()]})


def _evidence(dimension: str = "pricing") -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev_1",
        task_id="task_1",
        competitor_name="Cursor",
        dimension=dimension,
        claim="Pro plan costs 20 USD per month",
        value="20 USD",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        quote="Cursor Pro costs 20 USD per month.",
        confidence=0.9,
        extracted_at="2026-01-01T00:00:00Z",
    )


def test_normalize_url_removes_tracking_params():
    assert normalize_url("HTTPS://Example.com/a/?utm_source=x&b=1#top") == "https://example.com/a?b=1"


def test_normalize_url_handles_ports_fragments_and_query_order():
    assert normalize_url("http://Example.com:80/a/#top") == "http://example.com/a"
    assert normalize_url("https://Example.com:443/a?z=2&utm_term=x&a=1") == (
        "https://example.com/a?a=1&z=2"
    )


def test_dedupe_search_results_preserves_first():
    results = [
        SearchResult(
            title="A",
            url="https://example.com?a=1&utm_campaign=x",
            snippet="",
            provider="s",
        ),
        SearchResult(title="B", url="https://example.com:443/?a=1#top", snippet="", provider="s"),
    ]
    assert dedupe_search_results(results)[0].title == "A"
    assert len(dedupe_search_results(results)) == 1


@pytest.mark.asyncio
async def test_search_tool_returns_validated_result():
    result = await SearchTool(SearchServiceStub()).run("query", max_results=5)
    assert result.total == 1


@pytest.mark.asyncio
async def test_webpage_tool_returns_ok_result(stub_fetch):
    result = await WebpageTool(stub_fetch).run("https://example.com")
    assert result.ok
    assert result.page.url == "https://example.com"


@pytest.mark.asyncio
async def test_extraction_tool_uses_llm_schema(fake_llm):
    fake_llm.set_response(
        keyword="Extract concise evidence",
        response={"evidences": [_evidence().model_dump()]},
    )
    result = await ExtractionTool(fake_llm).run(
        task_id="task_1",
        competitor_name="Cursor",
        dimension="pricing",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        text="Cursor Pro costs 20 USD per month.",
    )
    assert result.evidences[0].evidence_id == "ev_1"


@pytest.mark.asyncio
async def test_extraction_tool_accepts_long_text_and_truncates_prompt():
    llm = RecordingLLM()

    result = await ExtractionTool(llm).run(
        task_id="task_1",
        competitor_name="Cursor",
        dimension="pricing",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        text=("Cursor   Pro costs 20 USD per month. " * 120),
    )

    prompt_text = str(llm.calls[0]["prompt"]).split("text=", 1)[1]
    assert len(prompt_text) <= 2000
    assert "  " not in prompt_text
    assert result.evidences[0].evidence_id == "ev_1"


@pytest.mark.asyncio
async def test_extraction_tool_cache_key_uses_prepared_text():
    llm = RecordingLLM()
    tool = ExtractionTool(llm, MemoryCache())
    common_prefix = "Cursor Pro pricing evidence " * 120

    first = await tool.run(
        task_id="task_1",
        competitor_name="Cursor",
        dimension="pricing",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        text=f"{common_prefix} first suffix",
    )
    second = await tool.run(
        task_id="task_2",
        competitor_name="Cursor",
        dimension="pricing",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        text=f"{common_prefix} second suffix",
    )

    assert len(llm.calls) == 1
    assert first.evidences[0].task_id == "task_1"
    assert second.evidences[0].task_id == "task_2"


@pytest.mark.asyncio
async def test_extraction_tool_reuses_cache(fake_llm):
    fake_llm.set_response(
        keyword="Extract concise evidence",
        response={"evidences": [_evidence().model_dump()]},
    )
    tool = ExtractionTool(fake_llm, MemoryCache())
    first = await tool.run(
        task_id="task_1",
        competitor_name="Cursor",
        dimension="pricing",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        text="Cursor Pro costs 20 USD per month.",
    )
    second = await tool.run(
        task_id="task_2",
        competitor_name="Cursor",
        dimension="pricing",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        text="Cursor Pro costs 20 USD per month.",
    )
    assert first.evidences[0].task_id == "task_1"
    assert second.evidences[0].task_id == "task_2"
    assert len(fake_llm.calls) == 1


def test_source_classifier_classifies_known_domains():
    result = SourceClassifierTool().run(
        source_id="src_1",
        url="https://techcrunch.com/story",
        title="Story",
        retrieved_at="2026-01-01T00:00:00Z",
    )
    assert result.source_type == "media"


def test_sufficiency_tool_reports_missing_dimensions():
    result = SufficiencyTool().run(
        evidences=[_evidence("pricing")],
        dimensions=["pricing", "features"],
        threshold=0.6,
    )
    assert not result.is_sufficient
    assert result.missing_dimensions == ["features"]


def test_sufficiency_threshold_controls_result_with_missing_diagnostics():
    two_of_three = SufficiencyTool().run(
        evidences=[_evidence("pricing"), _evidence("features")],
        dimensions=["pricing", "features", "ecosystem"],
        threshold=0.6,
    )
    one_of_three = SufficiencyTool().run(
        evidences=[_evidence("pricing")],
        dimensions=["pricing", "features", "ecosystem"],
        threshold=0.6,
    )
    stricter = SufficiencyTool().run(
        evidences=[_evidence("pricing"), _evidence("features")],
        dimensions=["pricing", "features", "ecosystem"],
        threshold=0.8,
    )

    assert two_of_three.score == pytest.approx(2 / 3)
    assert two_of_three.is_sufficient
    assert two_of_three.missing_dimensions == ["ecosystem"]
    assert not one_of_three.is_sufficient
    assert not stricter.is_sufficient
