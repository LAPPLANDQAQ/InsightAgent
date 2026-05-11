"""Reranker protocol."""

from typing import Protocol

from app.rag.schemas import RetrievedChunk


class RerankerProtocol(Protocol):
    """Protocol for retrieval rerankers."""

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """Return reranked candidates."""
        ...
