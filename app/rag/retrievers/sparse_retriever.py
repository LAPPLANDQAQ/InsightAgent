"""Sparse keyword retriever with optional BM25-style scoring."""

import re
from collections import Counter

from app.rag.schemas import ChildChunk, RetrievedChunk


class SparseRetriever:
    """Retrieve chunks by token overlap and exact phrase bonus."""

    name = "sparse"

    def __init__(self, chunks: list[ChildChunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        """Return top sparse matches for query."""
        query_tokens = self._tokens(query)
        if not query_tokens or not self.chunks:
            return []
        scored: list[tuple[float, list[str], ChildChunk]] = []
        for chunk in self.chunks:
            chunk_tokens = Counter(self._tokens(chunk.text))
            matched = sorted(set(query_tokens) & set(chunk_tokens))
            if not matched:
                continue
            score = float(sum(chunk_tokens[token] for token in query_tokens))
            if query.lower() in chunk.text.lower():
                score += 5.0
            scored.append((score, matched, chunk))
        scored.sort(key=lambda item: (-item[0], item[2].chunk_id))
        return [
            RetrievedChunk(
                chunk=chunk,
                retriever_name=self.name,
                rank=index,
                score=score,
                matched_terms=matched,
            )
            for index, (score, matched, chunk) in enumerate(scored[:top_k], start=1)
        ]

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\w]+", text.lower())
