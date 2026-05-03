"""Writer agent."""

from typing import Any

from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient


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
            report = self._fallback_report(state)
            issues = [f"writer_fallback: {exc}"]
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
            f"# {plan.get('market', '竞品分析')} 调研报告",
            "",
            "## 调研范围",
            f"- 竞品：{', '.join(plan.get('competitors', []))}",
            f"- 维度：{', '.join(plan.get('dimensions', []))}",
            "",
            "## 市场摘要",
            str(analysis.get("market_summary", "暂无摘要")),
            "",
            "## 维度分析",
        ]
        for item in analysis.get("dimension_analysis", []):
            refs = ", ".join(item.get("evidence_refs", []))
            lines.extend(
                [
                    f"### {item.get('dimension', '')}",
                    item.get("comparison_summary", ""),
                    f"- 证据：{refs}",
                ]
            )
        lines.extend(["", "## 建议", str(analysis.get("recommendation", "继续补充证据。"))])
        return "\n".join(lines)
