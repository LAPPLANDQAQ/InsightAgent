"""Evidence schema tests."""

import pytest
from pydantic import ValidationError

from app.infra.db.models import EvidenceRow
from app.schemas.evidence import EvidenceItem, to_lite


def test_to_lite_drops_quote():
    evidence = EvidenceItem(
        evidence_id="ev_x",
        task_id="task_1",
        competitor_name="Cursor",
        dimension="pricing",
        claim="Pro plan costs 20 USD per month",
        value="20 USD",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        quote="Pricing page excerpt.",
        confidence=0.9,
        extracted_at="2026-01-01T00:00:00Z",
    )
    lite = to_lite(evidence)
    assert not hasattr(lite, "quote")
    assert lite.evidence_id == "ev_x"


def test_evidence_claim_accepts_240_characters():
    evidence = EvidenceItem(
        evidence_id="ev_x",
        task_id="task_1",
        competitor_name="Cursor",
        dimension="pricing",
        claim="x" * 240,
        value="20 USD",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        quote="Pricing page excerpt.",
        confidence=0.9,
        extracted_at="2026-01-01T00:00:00Z",
    )

    assert len(evidence.claim) == 240


def test_evidence_claim_rejects_241_characters():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_x",
            task_id="task_1",
            competitor_name="Cursor",
            dimension="pricing",
            claim="x" * 241,
            value="20 USD",
            source_id="src_1",
            source_url="https://cursor.com/pricing",
            quote="Pricing page excerpt.",
            confidence=0.9,
            extracted_at="2026-01-01T00:00:00Z",
        )


def test_evidence_db_claim_column_matches_schema_length():
    assert EvidenceRow.__table__.c.claim.type.length == 240
