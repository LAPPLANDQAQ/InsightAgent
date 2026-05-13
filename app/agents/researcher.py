"""Researcher agent."""

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

from app.agents.base import AgentBase
from app.schemas.evidence import EvidenceItem
from app.schemas.source import SourceItem
from app.tools.agent_observability import get_agent_logger, redact_issue
from app.tools.extraction_tool import ExtractionTool
from app.tools.search_tool import SearchTool
from app.tools.source_classifier_tool import SourceClassifierTool
from app.tools.sufficiency_tool import SufficiencyTool
from app.tools.webpage_tool import WebpageTool

logger = get_agent_logger(__name__)


class Researcher(AgentBase):
    """Gather sources and extract evidence."""

    name = "researcher"

    def __init__(
        self,
        search_tool: SearchTool,
        webpage_tool: WebpageTool,
        extraction_tool: ExtractionTool,
        classifier_tool: SourceClassifierTool,
        sufficiency_tool: SufficiencyTool,
        *,
        threshold: float = 0.6,
        max_rounds: int = 3,
    ) -> None:
        self.search_tool = search_tool
        self.webpage_tool = webpage_tool
        self.extraction_tool = extraction_tool
        self.classifier_tool = classifier_tool
        self.sufficiency_tool = sufficiency_tool
        self.threshold = threshold
        self.max_rounds = max_rounds

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Research competitors and dimensions.

        Args:
            state: Workflow state containing a research plan.

        Returns:
            State update with competitors, sources, evidences, and sufficiency.
        """
        plan = state.get("plan") or {}
        task_id = str(state.get("task_id", "task"))
        issues: list[str] = []
        competitors = []
        for name in plan.get("competitors", []):
            item, item_issues = await self._research_competitor(task_id, name, plan)
            competitors.append(item)
            issues.extend(item_issues)
        evidences = [ev for item in competitors for ev in item["evidences"]]
        sufficiency = self.sufficiency_tool.run(
            evidences=[EvidenceItem.model_validate(ev) for ev in evidences],
            dimensions=list(plan.get("dimensions", [])),
            threshold=float(state.get("sufficiency_threshold", self.threshold)),
        )
        return {
            "competitors": competitors,
            "sufficiency": sufficiency.model_dump(),
            "current_stage": self.name,
            "issues": issues,
        }

    async def _research_competitor(
        self,
        task_id: str,
        competitor_name: str,
        plan: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        sources: list[SourceItem] = []
        evidences: list[EvidenceItem] = []
        issues: list[str] = []
        queries = (plan.get("search_queries", {}).get(competitor_name) or [competitor_name])[
            : self.max_rounds
        ]
        search_outputs = await asyncio.gather(
            *(
                self._run_search_query(task_id, competitor_name, query)
                for query in queries
            ),
            return_exceptions=True,
        )
        for query, search_output in zip(queries, search_outputs, strict=False):
            if isinstance(search_output, BaseException):
                error = redact_issue(str(search_output))
                issues.append(f"search_failed:{competitor_name}:{error}")
                continue
            search_result = cast(Any, search_output)
            issues.extend(search_result.issues)
            if not search_result.results:
                issues.append(f"search_empty:{competitor_name}:{query}")
                continue
            for index, result in enumerate(search_result.results):
                source_id = f"src_{competitor_name}_{len(sources) + 1}".replace(" ", "_")
                source = self.classifier_tool.run(
                    source_id=source_id,
                    url=result.url,
                    title=result.title,
                    retrieved_at=datetime.now(UTC).isoformat(),
                )
                sources.append(source)
                try:
                    page = await self.webpage_tool.run(result.url)
                except Exception as exc:
                    logger.exception(
                        "researcher_fetch_failed",
                        extra={
                            "task_id": task_id,
                            "stage": self.name,
                            "competitor": competitor_name,
                            "url": result.url,
                        },
                    )
                    error = redact_issue(str(exc))
                    issues.append(f"fetch_failed:{competitor_name}:{result.url}:{error}")
                    continue
                if page.page.error:
                    error = redact_issue(str(page.page.error))
                    issues.append(f"fetch_failed:{competitor_name}:{result.url}:{error}")
                    continue
                if not page.page.text.strip():
                    issues.append(f"fetch_empty:{competitor_name}:{result.url}")
                    continue
                dimensions = list(plan.get("dimensions", []))
                dimension_outputs = await asyncio.gather(
                    *(
                        self._run_dimension_extract(
                            task_id,
                            competitor_name,
                            dimension,
                            source,
                            page.page.text,
                            index,
                        )
                        for dimension in dimensions
                    ),
                    return_exceptions=True,
                )
                for dimension, output in zip(dimensions, dimension_outputs, strict=False):
                    if isinstance(output, BaseException):
                        error = redact_issue(str(output))
                        issues.append(
                            f"extract_failed:{competitor_name}:{dimension}:{source.url}:{error}"
                        )
                        continue
                    evidence, extract_issues = output
                    evidences.extend(evidence)
                    issues.extend(extract_issues)
        return {
            "name": competitor_name,
            "sources": [source.model_dump() for source in sources],
            "evidences": [evidence.model_dump() for evidence in evidences],
        }, issues

    async def _run_search_query(self, task_id: str, competitor_name: str, query: str):
        try:
            return await self.search_tool.run(query, max_results=3)
        except Exception:
            logger.exception(
                "researcher_search_failed",
                extra={
                    "task_id": task_id,
                    "stage": self.name,
                    "competitor": competitor_name,
                },
            )
            raise

    async def _run_dimension_extract(
        self,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source: SourceItem,
        text: str,
        index: int,
    ) -> tuple[list[EvidenceItem], list[str]]:
        try:
            return await self._extract_or_fallback(
                task_id,
                competitor_name,
                dimension,
                source,
                text,
                index,
            )
        except Exception:
            logger.exception(
                "researcher_dimension_extract_failed",
                extra={
                    "task_id": task_id,
                    "stage": self.name,
                    "competitor": competitor_name,
                    "dimension": dimension,
                    "source_id": source.source_id,
                },
            )
            raise

    async def _extract_or_fallback(
        self,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source: SourceItem,
        text: str,
        index: int,
    ) -> tuple[list[EvidenceItem], list[str]]:
        try:
            result = await self.extraction_tool.run(
                task_id=task_id,
                competitor_name=competitor_name,
                dimension=dimension,
                source_id=source.source_id,
                source_url=source.url,
                text=text,
                max_evidence=2,
            )
            if result.evidences:
                return result.evidences, []
        except Exception as exc:
            logger.exception(
                "researcher_extract_failed",
                extra={
                    "task_id": task_id,
                    "stage": self.name,
                    "competitor": competitor_name,
                    "dimension": dimension,
                    "source_id": source.source_id,
                },
            )
            error = redact_issue(str(exc))
            issue = f"extract_failed:{competitor_name}:{dimension}:{source.url}:{error}"
            fallback = self._fallback_evidence(
                task_id,
                competitor_name,
                dimension,
                source,
                text,
                index,
            )
            return [fallback], [issue]
        fallback = self._fallback_evidence(
            task_id,
            competitor_name,
            dimension,
            source,
            text,
            index,
        )
        return [fallback], [f"extract_empty:{competitor_name}:{dimension}:{source.url}"]

    @staticmethod
    def _fallback_evidence(
        task_id: str,
        competitor_name: str,
        dimension: str,
        source: SourceItem,
        text: str,
        index: int,
    ) -> EvidenceItem:
        snippet = " ".join(text.split())[:180] or f"{competitor_name} public information"
        safe_source = source.source_id.replace(" ", "_")
        safe_dimension = dimension.replace(" ", "_")
        return EvidenceItem(
            evidence_id=f"ev_{safe_source}_{safe_dimension}_{index}".replace(" ", "_"),
            task_id=task_id,
            competitor_name=competitor_name,
            dimension=dimension,
            claim=f"{competitor_name} {dimension} evidence",
            value=snippet[:80],
            source_id=source.source_id,
            source_url=source.url,
            quote=snippet,
            confidence=0.5,
            extracted_at=datetime.now(UTC).isoformat(),
        )
