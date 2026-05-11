"""Tests for report quality metrics."""

from app.rag.evaluation.report_quality import dimension_coverage, unsupported_claim_count


def test_report_quality_metrics():
    """Report quality tracks dimension coverage and unsupported bullets."""
    coverage = dimension_coverage(
        ["pricing", "features"],
        [{"dimension": "pricing", "confidence": 0.8}],
    )

    assert coverage["score"] == 0.5
    assert unsupported_claim_count("- unsupported\n- supported [ev_1]") == 1
