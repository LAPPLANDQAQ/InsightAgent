"""Tests for citation metrics."""

from app.rag.evaluation.citation_metrics import citation_validity, extract_citation_refs


def test_citation_validity_detects_invalid_refs():
    """Citation validity compares report refs to evidence ids."""
    result = citation_validity("A [ev_1] B [ev_bad]", [{"evidence_id": "ev_1"}])

    assert extract_citation_refs("A [ev_1]") == ["ev_1"]
    assert result["score"] == 0.5
    assert result["invalid_refs"] == ["ev_bad"]
