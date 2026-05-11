"""Report quality metrics."""

from typing import Any


def dimension_coverage(dimensions: list[str], notes: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute dimension coverage from research notes."""
    covered = {
        str(note.get("dimension"))
        for note in notes
        if float(note.get("confidence") or 0.0) > 0.5
    }
    missing = [dimension for dimension in dimensions if dimension not in covered]
    score = 1.0 if not dimensions else (len(dimensions) - len(missing)) / len(dimensions)
    return {"score": score, "missing_dimensions": missing}


def unsupported_claim_count(report: str) -> int:
    """Count simple unsupported claim markers in a report."""
    lines = [line for line in report.splitlines() if line.strip().startswith("-")]
    return sum(1 for line in lines if "[ev_" not in line)
