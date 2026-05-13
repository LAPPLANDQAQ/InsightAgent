"""Writer agent."""

from typing import Any

from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient
from app.tools.agent_observability import get_agent_logger, redact_issue

logger = get_agent_logger(__name__)


class Writer(AgentBase):
    """Write the final Markdown report."""

    name = "writer"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate a Markdown report.

        Args:
            state: Workflow state containing plan, competitors, and analysis.

        Returns:
            State update with draft and final report fields.
        """
        prompt = self._prompt(state)
        try:
            report = await self.llm.invoke(
                prompt=prompt,
                model_role="heavy",
                max_tokens=3000,
                temperature=0.2,
            )
        except Exception as exc:
            logger.exception(
                "writer_llm_failed",
                extra={"task_id": state.get("task_id"), "stage": self.name},
            )
            report = self._fallback_report(state)
            issues = [f"writer_fallback: {redact_issue(str(exc))}"]
        else:
            issues = []
        return {
            "draft_report": str(report),
            "final_report": str(report),
            "current_stage": self.name,
            "issues": issues,
        }

    @staticmethod
    def _prompt(state: dict[str, Any]) -> str:
        return (
            "Write a concise Chinese Markdown competitive analysis report with evidence ids.\n"
            f"plan={state.get('plan')}\n"
            f"analysis={state.get('analysis')}\n"
            f"competitors={state.get('competitors')}"
        )

    @staticmethod
    def _fallback_report(state: dict[str, Any]) -> str:
        plan = state.get("plan") or {}
        analysis = state.get("analysis") or {}
        lines = [
            f"# {plan.get('market', 'Competitive Analysis')} Research Report",
            "",
            "## Scope",
            f"- Competitors: {', '.join(plan.get('competitors', []))}",
            f"- Dimensions: {', '.join(plan.get('dimensions', []))}",
            "",
            "## Market Summary",
            str(analysis.get("market_summary", "No summary available.")),
            "",
            "## Dimension Analysis",
        ]
        for item in analysis.get("dimension_analysis", []):
            refs = [
                f"[{str(ref).strip()}]"
                for ref in item.get("evidence_refs", [])
                if str(ref).strip()
            ]
            evidence_line = ", ".join(refs) if refs else "not available"
            lines.extend(
                [
                    f"### {item.get('dimension', '')}",
                    item.get("comparison_summary", ""),
                    f"- Evidence: {evidence_line}",
                ]
            )
        lines.extend(
            [
                "",
                "## Recommendation",
                str(analysis.get("recommendation", "Continue collecting evidence.")),
            ]
        )
        return "\n".join(lines)
