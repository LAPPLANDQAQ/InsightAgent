"""Research sufficiency tool."""

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceItem, EvidenceLite


class DimensionCoverage(BaseModel):
    """Evidence coverage for one dimension."""

    dimension: str
    evidence_count: int = Field(ge=0)
    sufficient: bool


class SufficiencyResult(BaseModel):
    """Validated sufficiency assessment."""

    score: float = Field(ge=0.0, le=1.0)
    is_sufficient: bool
    missing_dimensions: list[str] = Field(default_factory=list)
    coverage: list[DimensionCoverage]


class SufficiencyTool:
    """Assess whether gathered evidence covers requested dimensions."""

    def run(
        self,
        *,
        evidences: list[EvidenceItem | EvidenceLite],
        dimensions: list[str],
        threshold: float = 0.6,
        min_evidence_per_dimension: int = 1,
    ) -> SufficiencyResult:
        """Assess evidence sufficiency.

        Args:
            evidences: Evidence items to evaluate.
            dimensions: Required research dimensions.
            threshold: Minimum coverage score.
            min_evidence_per_dimension: Evidence count required per dimension.

        Returns:
            Validated sufficiency result.
        """
        counts = {dimension: 0 for dimension in dimensions}
        for evidence in evidences:
            if evidence.dimension in counts:
                counts[evidence.dimension] += 1
        coverage = [
            DimensionCoverage(
                dimension=dimension,
                evidence_count=count,
                sufficient=count >= min_evidence_per_dimension,
            )
            for dimension, count in counts.items()
        ]
        enough = sum(1 for item in coverage if item.sufficient)
        score = enough / len(dimensions) if dimensions else 0.0
        missing = [item.dimension for item in coverage if not item.sufficient]
        return SufficiencyResult(
            score=score,
            is_sufficient=score >= threshold,
            missing_dimensions=missing,
            coverage=coverage,
        )
