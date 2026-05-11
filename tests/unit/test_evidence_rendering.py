"""Tests for evidence rendering helpers."""

from frontend.components.evidence_viewer import (
    build_evidence_lookup,
    citation_summary,
    evidence_detail,
    extract_evidence_refs,
)


def test_evidence_helpers_extract_lookup_and_summarize():
    evidences = [{"evidence_id": "ev_1", "quote": "Quote"}]
    markdown = "Claim [ev_1] and missing [ev_2]"

    assert extract_evidence_refs(markdown) == ["ev_1", "ev_2"]
    assert build_evidence_lookup(evidences)["ev_1"]["quote"] == "Quote"
    assert evidence_detail("ev_missing", evidences)["missing"]
    assert citation_summary(markdown, evidences)["missing_refs"] == ["ev_2"]
