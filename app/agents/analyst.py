"""Analyst agent."""

from typing import Any

from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient
from app.schemas.analysis import AnalysisResult, DimensionAnalysis
from app.schemas.evidence import EvidenceItem, to_lite


class Analyst(AgentBase):
    """Analyze evidence into competitive findings."""

    name = "analyst"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Create analysis from collected evidence.

        Args:
            state: Workflow state with plan and competitor evidence.

        Returns:
            State update with analysis result.
        """
        plan = state.get("plan") or {}
        evidences = [
            EvidenceItem.model_validate(raw)
            for competitor in state.get("competitors", [])
            for raw in competitor.get("evidences", [])
        ]
        prompt = self._prompt(plan, evidences)
        try:
            analysis = await self.llm.invoke(
                prompt=prompt,
                model_role="heavy",
                schema=AnalysisResult,
                max_tokens=2400,
                temperature=0.2,
            )
        except Exception as exc:
            analysis = self._fallback_analysis(plan, evidences)
            issues = [*state.get("issues", []), f"analyst_fallback: {exc}"]
        else:
            issues = list(state.get("issues", []))
        return {"analysis": analysis.model_dump(), "current_stage": self.name, "issues": issues}

    @staticmethod
    def _prompt(plan: dict[str, Any], evidences: list[EvidenceItem]) -> str:
        lite = [to_lite(evidence).model_dump() for evidence in evidences]
        return (
            "Analyze competitive evidence. Use only evidence_refs from input.\n"
            f"plan={plan}\n"
            f"evidence_lite={lite}"
        )

    @staticmethod
    def _fallback_analysis(plan: dict[str, Any], evidences: list[EvidenceItem]) -> AnalysisResult:
        dimensions = list(plan.get("dimensions") or [])
        competitors = list(plan.get("competitors") or [])
        dimension_analysis: list[DimensionAnalysis] = []
        for dimension in dimensions:
            refs = [
                evidence.evidence_id
                for evidence in evidences
                if evidence.dimension == dimension
            ]
            dimension_analysis.append(
                DimensionAnalysis(
                    dimension=dimension,
                    comparison_summary=f"Collected {len(refs)} evidence items for {dimension}.",
                    key_findings=[
                        f"{dimension} has public evidence across researched competitors."
                    ],
                    evidence_refs=refs[:1] or ["missing_evidence"],
                    confidence=0.7 if refs else 0.3,
                    limitations=[] if refs else ["No direct evidence was extracted."],
                )
            )
        return AnalysisResult(
            market_summary=f"Market scope: {plan.get('market', 'competitive analysis')}.",
            competitor_positioning={
                name: f"{name} is covered by gathered evidence." for name in competitors
            },
            dimension_analysis=dimension_analysis,
            opportunities=["Compare evidence-backed differentiators by dimension."],
            risks=["Findings depend on public page availability."],
            recommendation="Prioritize dimensions with stronger evidence coverage.",
        )
