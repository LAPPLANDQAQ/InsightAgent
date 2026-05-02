"""Evidence schema tests."""

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
