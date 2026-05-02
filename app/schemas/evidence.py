"""Evidence data contracts."""

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Full evidence item used by research and persistence."""

    evidence_id: str
    task_id: str
    competitor_name: str
    dimension: str
    claim: str = Field(max_length=80)
    value: str
    source_id: str
    source_url: str
    quote: str = Field(max_length=200)
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: str


class EvidenceLite(BaseModel):
    """Evidence view for analysis without raw quotes."""

    evidence_id: str
    competitor_name: str
    dimension: str
    claim: str
    value: str
    source_url: str
    confidence: float = Field(ge=0.0, le=1.0)


def to_lite(evidence: EvidenceItem) -> EvidenceLite:
    """Convert full evidence into the analysis-safe lite view.

    Args:
        evidence: Full evidence item containing the raw quote.

    Returns:
        Lite evidence without the quote or source identifier.
    """
    return EvidenceLite(
        evidence_id=evidence.evidence_id,
        competitor_name=evidence.competitor_name,
        dimension=evidence.dimension,
        claim=evidence.claim,
        value=evidence.value,
        source_url=evidence.source_url,
        confidence=evidence.confidence,
    )
