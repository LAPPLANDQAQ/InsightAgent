"""Retrieval quality metrics."""

import math


def hit_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Return 1 when any relevant id is present in the top k results."""
    if k <= 0 or not ranked_ids or not relevant_ids:
        return 0.0
    return 1.0 if any(item in relevant_ids for item in ranked_ids[:k]) else 0.0


def mean_reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    """Return reciprocal rank of the first relevant result."""
    if not ranked_ids or not relevant_ids:
        return 0.0
    for index, item in enumerate(ranked_ids, start=1):
        if item in relevant_ids:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Return binary nDCG@k."""
    if k <= 0 or not ranked_ids or not relevant_ids:
        return 0.0
    dcg = 0.0
    for index, item in enumerate(ranked_ids[:k], start=1):
        if item in relevant_ids:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(relevant_ids), k)
    ideal = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / ideal if ideal else 0.0
