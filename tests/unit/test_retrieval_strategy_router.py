"""Tests for RetrievalStrategyRouter."""

import pytest
from pydantic import ValidationError

from app.rag.strategy.retrieval_strategy_router import (
    RetrievalStrategyConfig,
    RetrievalStrategyRouter,
)


def test_retrieval_strategy_router_dimension_rules():
    """Strategy router adapts sparse/dense weights and freshness hints."""
    router = RetrievalStrategyRouter()

    assert router.route("pricing").sparse_weight > router.route("pricing").dense_weight
    assert router.route("architecture").dense_weight > router.route("architecture").sparse_weight
    assert router.route("news").freshness_hint
    assert router.route("unknown").strategy_name == "balanced_default"


def test_retrieval_strategy_config_rejects_zero_weights():
    """Strategy config validates weights."""
    with pytest.raises(ValidationError):
        RetrievalStrategyConfig(
            strategy_name="bad",
            sparse_weight=0,
            dense_weight=0,
            sparse_top_k=1,
            dense_top_k=1,
            final_top_k=1,
        )
