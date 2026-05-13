"""Agent fallback, critic, and researcher hardening tests."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.agents.critic import Critic
from app.agents.planner import Planner
from app.agents.researcher import Researcher
from app.agents.writer import Writer
from app.infra.llm.base import ModelRole
from app.infra.search.base import SearchResult
from app.schemas.evidence import EvidenceItem
from app.schemas.source import SourceItem
from app.tools.sufficiency_tool import SufficiencyTool


class FailingLLM:
    """LLM stub that always raises a secret-bearing error."""

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
        raise RuntimeError("failed with api_key=sk-secret token=abc123")


class ConcurrentSearchTool:
    """Search tool stub that exposes concurrent execution."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def run(self, query: str, max_results: int = 5):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        if "bad" in query:
            raise RuntimeError("search failed with api_key=sk-secret")
        return type(
            "SearchToolResult",
            (),
            {
                "issues": [],
                "results": [
                    SearchResult(
                        title="Cursor",
                        url="https://cursor.com/pricing",
                        snippet="pricing",
                        provider="stub",
                    )
                ],
            },
        )()


class StaticWebpageTool:
    """Webpage tool stub returning deterministic text."""

    async def run(self, url: str, timeout: float = 10.0):
        page = type(
            "Page",
            (),
            {"error": None, "text": "Cursor Pro costs 20 USD per month."},
        )()
        return type("WebpageToolResult", (), {"page": page})()


class ConcurrentExtractionTool:
    """Extraction tool stub that exposes concurrent dimension extraction."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def run(
        self,
        *,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source_id: str,
        source_url: str,
        text: str,
        max_evidence: int = 5,
    ):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        if dimension == "features":
            raise RuntimeError("extract failed with token=sk-secret")
        evidence = _evidence(task_id, competitor_name, dimension, source_id, source_url)
        return type("EvidenceExtractionResult", (), {"evidences": [evidence]})()


class ClassifierTool:
    """Source classifier stub."""

    def run(
        self,
        *,
        source_id: str,
        url: str,
        title: str,
        retrieved_at: str,
        published_at: str | None = None,
    ) -> SourceItem:
        return SourceItem(
            source_id=source_id,
            url=url,
            domain="cursor.com",
            title=title,
            source_type="official",
            credibility_score=0.9,
            classification_method="rule",
            published_at=published_at,
            retrieved_at=retrieved_at,
        )


def _evidence(
    task_id: str = "task_1",
    competitor_name: str = "Cursor",
    dimension: str = "pricing",
    source_id: str = "src_1",
    source_url: str = "https://cursor.com/pricing",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"ev_{dimension}",
        task_id=task_id,
        competitor_name=competitor_name,
        dimension=dimension,
        claim=f"{competitor_name} {dimension} evidence",
        value="20 USD",
        source_id=source_id,
        source_url=source_url,
        quote="Cursor Pro costs 20 USD per month.",
        confidence=0.9,
        extracted_at=datetime.now(UTC).isoformat(),
    )


def _state_with_report(report: str) -> dict:
    return {
        "plan": {"dimensions": ["pricing"]},
        "analysis": {"dimension_analysis": [{"dimension": "pricing", "evidence_refs": ["ev_1"]}]},
        "competitors": [
            {
                "evidences": [
                    _evidence(dimension="pricing")
                    .model_copy(update={"evidence_id": "ev_1"})
                    .model_dump()
                ]
            }
        ],
        "final_report": report,
    }


def test_writer_fallback_brackets_evidence_refs():
    report = Writer._fallback_report(
        {
            "plan": {"market": "AI tools", "competitors": ["Cursor"], "dimensions": ["pricing"]},
            "analysis": {
                "dimension_analysis": [
                    {
                        "dimension": "pricing",
                        "comparison_summary": "Cursor pricing was collected.",
                        "evidence_refs": ["ev_1", " ev_2 "],
                    }
                ]
            },
        }
    )

    assert "- Evidence: [ev_1], [ev_2]" in report


def test_writer_fallback_uses_not_available_without_refs():
    report = Writer._fallback_report(
        {
            "plan": {"market": "AI tools", "competitors": ["Cursor"], "dimensions": ["pricing"]},
            "analysis": {
                "dimension_analysis": [
                    {"dimension": "pricing", "comparison_summary": "No refs.", "evidence_refs": []}
                ]
            },
        }
    )

    assert "- Evidence: not available" in report


def test_critic_ignores_metadata_bullets_but_flags_real_claims():
    metadata_report = "\n".join(
        [
            "- Competitors: Cursor",
            "- Dimensions: pricing",
            "- Evidence: [ev_1]",
            "- Scope: public pages",
            "- Sources: official pages",
        ]
    )
    real_claim_report = "- Cursor is always cheaper than competitors."

    metadata_issues = Critic()._rule_issues(_state_with_report(metadata_report))
    real_claim_issues = Critic()._rule_issues(_state_with_report(real_claim_report))

    assert not [issue for issue in metadata_issues if issue.issue_type == "unsupported_claim"]
    assert [issue for issue in real_claim_issues if issue.issue_type == "unsupported_claim"]


def test_writer_fallback_does_not_create_metadata_unsupported_claims():
    report = Writer._fallback_report(
        {
            "plan": {"market": "AI tools", "competitors": ["Cursor"], "dimensions": ["pricing"]},
            "analysis": {
                "dimension_analysis": [
                    {
                        "dimension": "pricing",
                        "comparison_summary": "Cursor pricing was collected.",
                        "evidence_refs": ["ev_1"],
                    }
                ]
            },
        }
    )

    issues = Critic()._rule_issues(_state_with_report(report))

    assert not [issue for issue in issues if issue.issue_type == "unsupported_claim"]


@pytest.mark.asyncio
async def test_planner_and_writer_fallback_issues_redact_secrets():
    planner_result = await Planner(FailingLLM()).run({"user_query": "AI coding assistants"})
    writer_result = await Writer(FailingLLM()).run({"plan": {}, "analysis": {}})

    issue_text = " ".join(planner_result["issues"] + writer_result["issues"])
    assert "api_key=[REDACTED]" in issue_text
    assert "token=[REDACTED]" in issue_text
    assert "sk-secret" not in issue_text
    assert "abc123" not in issue_text


@pytest.mark.asyncio
async def test_researcher_runs_search_queries_concurrently_and_redacts_failure():
    search_tool = ConcurrentSearchTool()
    researcher = Researcher(
        search_tool,
        StaticWebpageTool(),
        ConcurrentExtractionTool(),
        ClassifierTool(),
        SufficiencyTool(),
    )

    result = await researcher.run(
        {
            "task_id": "task_1",
            "plan": {
                "competitors": ["Cursor"],
                "dimensions": ["pricing"],
                "search_queries": {"Cursor": ["bad query", "good query"]},
            },
        }
    )

    assert search_tool.max_active > 1
    assert result["competitors"][0]["evidences"]
    assert any("api_key=[REDACTED]" in issue for issue in result["issues"])
    assert "sk-secret" not in " ".join(result["issues"])


@pytest.mark.asyncio
async def test_researcher_runs_dimension_extraction_concurrently_and_keeps_successes():
    extraction_tool = ConcurrentExtractionTool()
    researcher = Researcher(
        ConcurrentSearchTool(),
        StaticWebpageTool(),
        extraction_tool,
        ClassifierTool(),
        SufficiencyTool(),
    )

    result = await researcher.run(
        {
            "task_id": "task_1",
            "plan": {
                "competitors": ["Cursor"],
                "dimensions": ["pricing", "features"],
                "search_queries": {"Cursor": ["good query"]},
            },
        }
    )

    evidences = result["competitors"][0]["evidences"]
    assert extraction_tool.max_active > 1
    assert {evidence["dimension"] for evidence in evidences} == {"pricing", "features"}
    assert any("token=[REDACTED]" in issue for issue in result["issues"])
    assert "sk-secret" not in " ".join(result["issues"])


def test_critic_ignores_chinese_metadata_bullets_with_full_width_colon():
    report = "\n".join(
        [
            "- 竞品：Cursor",
            "- 维度：定价",
            "- 证据：[ev_1]",
        ]
    )
    issues = Critic()._rule_issues(_state_with_report(report))
    assert not [issue for issue in issues if issue.issue_type == "unsupported_claim"]
