"""ResearchPlan schema tests."""

import pytest
from pydantic import ValidationError

from app.schemas.plan import ResearchPlan


def test_required_fields_match_passes():
    plan = ResearchPlan(
        market="AI coding assistants",
        competitors=["Cursor", "Copilot"],
        dimensions=["pricing", "features", "ecosystem"],
        search_queries={"Cursor": ["Cursor pricing"]},
        required_fields={
            "pricing": ["price"],
            "features": ["capabilities"],
            "ecosystem": ["integrations"],
        },
    )
    assert plan.market == "AI coding assistants"


def test_required_fields_mismatch_fails():
    with pytest.raises(ValidationError, match="must match dimensions"):
        ResearchPlan(
            market="x",
            competitors=["a", "b"],
            dimensions=["pricing", "features", "ecosystem"],
            search_queries={},
            required_fields={"pricing": ["price"], "features": ["capabilities"]},
        )


def test_competitors_min_length():
    with pytest.raises(ValidationError):
        ResearchPlan(
            market="x",
            competitors=["a"],
            dimensions=["pricing", "features", "ecosystem"],
            search_queries={},
            required_fields={
                "pricing": [],
                "features": [],
                "ecosystem": [],
            },
        )
