"""Critic issue data contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class CriticIssue(BaseModel):
    """Issue found by the critic stage."""

    issue_type: Literal[
        "missing_evidence",
        "invalid_evidence_ref",
        "dimension_missing",
        "unsupported_claim",
        "weak_source",
        "format_error",
        "logic_gap",
    ]
    severity: Literal["low", "medium", "high"]
    target_stage: Literal["researcher", "analyst", "writer"]
    message: str
    related_ids: list[str] = Field(default_factory=list)
