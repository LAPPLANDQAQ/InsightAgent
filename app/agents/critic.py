"""Critic agent."""

import re
from typing import Any, Literal

from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient
from app.schemas.critic import CriticIssue

IssueType = Literal[
    "missing_evidence",
    "invalid_evidence_ref",
    "dimension_missing",
    "unsupported_claim",
    "weak_source",
    "format_error",
    "logic_gap",
]
TargetStage = Literal["researcher", "analyst", "writer"]


class Critic(AgentBase):
    """Rule-based quality gate for workflow outputs."""

    name = "critic"

    def __init__(self, llm: LLMClient | None = None, enable_llm: bool = False) -> None:
        self.llm = llm
        self.enable_llm = enable_llm

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Evaluate output quality.

        Args:
            state: Workflow state with analysis and report.

        Returns:
            State update with critic issues and final task status.
        """
        issues = self._rule_issues(state)
        status = "COMPLETED_WITH_WARNINGS" if issues or state.get("issues") else "COMPLETED"
        return {
            "critic_issues": [issue.model_dump() for issue in issues],
            "issues": [issue.message for issue in issues],
            "task_status": status,
            "current_stage": self.name,
            "critic_rounds": int(state.get("critic_rounds", 0)) + 1,
        }

    def _rule_issues(self, state: dict[str, Any]) -> list[CriticIssue]:
        evidence_ids = {
            evidence.get("evidence_id")
            for competitor in state.get("competitors", [])
            for evidence in competitor.get("evidences", [])
        }
        issues: list[CriticIssue] = []
        if not str(state.get("final_report", "")).strip():
            issues.append(self._issue("format_error", "writer", "final_report is empty"))
        analysis = state.get("analysis") or {}
        plan_dims = set((state.get("plan") or {}).get("dimensions", []))
        analysis_dims = {item.get("dimension") for item in analysis.get("dimension_analysis", [])}
        for missing in sorted(plan_dims - analysis_dims):
            issues.append(
                self._issue("dimension_missing", "analyst", f"missing dimension: {missing}")
            )
        for item in analysis.get("dimension_analysis", []):
            refs = item.get("evidence_refs", [])
            invalid = [ref for ref in refs if ref not in evidence_ids]
            if invalid:
                issues.append(
                    self._issue("invalid_evidence_ref", "analyst", f"invalid refs: {invalid}")
                )
        report = str(state.get("final_report") or state.get("draft_report") or "")
        for ref in sorted(set(re.findall(r"\[(ev_[A-Za-z0-9_\-]+)\]", report))):
            if ref not in evidence_ids:
                issues.append(
                    self._issue("invalid_evidence_ref", "writer", f"invalid report ref: {ref}")
                )
        unsupported = [
            line.strip()
            for line in report.splitlines()
            if line.strip().startswith("-") and "[ev_" not in line
        ]
        if unsupported:
            issues.append(
                self._issue(
                    "unsupported_claim",
                    "writer",
                    f"unsupported claim count: {len(unsupported)}",
                )
            )
        return issues

    @staticmethod
    def _issue(issue_type: IssueType, target_stage: TargetStage, message: str) -> CriticIssue:
        return CriticIssue(
            issue_type=issue_type,
            severity="medium",
            target_stage=target_stage,
            message=message,
            related_ids=[],
        )
