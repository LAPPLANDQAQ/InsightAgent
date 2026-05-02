"""Analysis result data contracts."""

from pydantic import BaseModel, Field


class DimensionAnalysis(BaseModel):
    """Analysis for one comparison dimension."""

    dimension: str
    comparison_summary: str
    key_findings: list[str]
    evidence_refs: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Complete analysis output."""

    market_summary: str
    competitor_positioning: dict[str, str]
    dimension_analysis: list[DimensionAnalysis]
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: str
