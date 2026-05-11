"""Optional cross-encoder reranker with lazy imports."""

from typing import Any

from app.rag.schemas import RetrievedChunk


class CrossEncoderReranker:
    """Lazy cross-encoder reranker that degrades safely when unavailable."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", batch_size: int = 8) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: Any | None = None

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """Rerank candidates or return originals if optional dependency is missing."""
        model = self._load_model()
        if model is None or not candidates:
            return candidates[:top_n] if top_n is not None else candidates
        pairs = [(query, item.chunk.text) for item in candidates]
        scores = model.predict(pairs, batch_size=self.batch_size)
        scored = sorted(zip(scores, candidates, strict=True), key=lambda item: -float(item[0]))
        if top_n is not None:
            scored = scored[:top_n]
        return [
            item.model_copy(update={"rank": rank, "rerank_score": float(score)})
            for rank, (score, item) in enumerate(scored, start=1)
        ]

    def _load_model(self) -> Any | None:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder
        except Exception:
            return None
        self._model = CrossEncoder(self.model_name)
        return self._model
