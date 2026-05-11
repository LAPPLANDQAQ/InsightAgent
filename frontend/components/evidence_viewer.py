"""Pure helpers for evidence-aware report rendering."""

import re
from typing import Any

EVIDENCE_REF_RE = re.compile(r"\[(ev_[A-Za-z0-9_\-]+)\]")


def extract_evidence_refs(markdown: str) -> list[str]:
    """Extract evidence ids from Markdown report text."""
    return EVIDENCE_REF_RE.findall(markdown)


def build_evidence_lookup(
    evidences: list[dict[str, Any]] | dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return evidence_id -> evidence detail mapping."""
    if isinstance(evidences, dict):
        values = evidences.values()
    else:
        values = evidences
    return {
        str(item.get("evidence_id")): item
        for item in values
        if isinstance(item, dict) and item.get("evidence_id")
    }


def citation_summary(
    markdown: str,
    evidences: list[dict[str, Any]] | dict[str, Any],
) -> dict[str, Any]:
    """Return simple citation count, density, and missing refs."""
    refs = extract_evidence_refs(markdown)
    lookup = build_evidence_lookup(evidences)
    words = [word for word in markdown.split() if word.strip()]
    return {
        "citation_count": len(refs),
        "citation_density": 0.0 if not words else len(refs) / len(words),
        "missing_refs": [ref for ref in refs if ref not in lookup],
    }


def evidence_detail(
    evidence_id: str,
    evidences: list[dict[str, Any]] | dict[str, Any],
) -> dict[str, Any]:
    """Return detail for one evidence id or an empty missing marker."""
    lookup = build_evidence_lookup(evidences)
    return lookup.get(evidence_id, {"evidence_id": evidence_id, "missing": True})
