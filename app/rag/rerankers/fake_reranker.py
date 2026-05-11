"""Deterministic fake reranker."""

from app.rag.schemas import RetrievedChunk


class FakeReranker:
    """Reranker used by tests and demos without external models."""

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """Rerank candidates by query token overlap."""
        terms = set(query.lower().split())
        scored = []
        for item in candidates:
            overlap = len(terms & set(item.chunk.text.lower().split()))
            scored.append((float(overlap), item))
        scored.sort(key=lambda item: (-item[0], item[1].chunk.chunk_id))
        if top_n is not None:
            scored = scored[:top_n]
        return [
            item.model_copy(update={"rank": rank, "rerank_score": score})
            for rank, (score, item) in enumerate(scored, start=1)
        ]
