"""Reciprocal Rank Fusion implementation."""

from app.rag.schemas import RetrievedChunk


def reciprocal_rank_fusion(
    result_sets: list[list[RetrievedChunk]],
    *,
    k: int = 60,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Fuse ranked result sets by chunk id."""
    by_id: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    metadata: dict[str, dict[str, float]] = {}
    for results in result_sets:
        for item in results:
            chunk_id = item.chunk.chunk_id
            by_id.setdefault(chunk_id, item)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + item.rank)
            metadata.setdefault(chunk_id, {})[f"{item.retriever_name}_score"] = item.score
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if top_k is not None:
        ordered = ordered[:top_k]
    fused: list[RetrievedChunk] = []
    for rank, (chunk_id, score) in enumerate(ordered, start=1):
        base = by_id[chunk_id]
        item_metadata = {**base.metadata, **metadata.get(chunk_id, {})}
        fused.append(
            base.model_copy(
                update={
                    "retriever_name": "rrf",
                    "rank": rank,
                    "final_score": score,
                    "metadata": item_metadata,
                }
            )
        )
    return fused
