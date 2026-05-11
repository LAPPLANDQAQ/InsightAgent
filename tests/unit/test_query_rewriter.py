"""Tests for QueryRewriter."""

from app.rag.query.query_rewriter import QueryRewriter


def test_query_rewriter_returns_original_and_deduped_variants():
    """QueryRewriter includes original query first and deduplicates."""
    variants = QueryRewriter().rewrite(
        "Cursor pricing",
        dimension="pricing",
        competitor_name="Cursor",
    )

    assert variants[0] == "Cursor pricing"
    assert len(variants) == len(set(variant.lower() for variant in variants))
