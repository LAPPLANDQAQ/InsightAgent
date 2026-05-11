"""Citation validity metrics."""

import re
from typing import Any


def extract_citation_refs(text: str) -> list[str]:
    """Extract evidence references like [ev_123] from text."""
    return re.findall(r"\[(ev_[A-Za-z0-9_\-]+)\]", text)


def citation_validity(report: str, evidences: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute how many report citations point to known evidence."""
    refs = extract_citation_refs(report)
    known = {str(item.get("evidence_id")) for item in evidences}
    invalid = [ref for ref in refs if ref not in known]
    score = 1.0 if not refs else (len(refs) - len(invalid)) / len(refs)
    return {"score": score, "total": len(refs), "invalid_refs": invalid}
