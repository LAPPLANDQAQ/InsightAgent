"""Tests for retrieval metrics."""

from app.rag.evaluation.retrieval_metrics import hit_at_k, mean_reciprocal_rank, ndcg_at_k


def test_retrieval_metrics_empty_and_positive_cases():
    """Retrieval metrics are safe for empty input and score hits."""
    assert hit_at_k([], {"a"}, 5) == 0.0
    assert mean_reciprocal_rank(["x", "a"], {"a"}) == 0.5
    assert ndcg_at_k(["a"], {"a"}, 1) == 1.0
