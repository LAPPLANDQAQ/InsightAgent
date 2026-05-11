"""Hybrid sparse plus dense retriever."""

from app.rag.fusion.rrf import reciprocal_rank_fusion
from app.rag.index.embedding_client import DeterministicEmbeddingClient, EmbeddingClientProtocol
from app.rag.retrievers.dense_retriever import DenseRetriever
from app.rag.retrievers.sparse_retriever import SparseRetriever
from app.rag.schemas import ChildChunk, RetrievedChunk


class HybridRetriever:
    """Combine sparse and dense retrievers through RRF."""

    def __init__(
        self,
        chunks: list[ChildChunk],
        embedding_client: EmbeddingClientProtocol | None = None,
        *,
        rrf_k: int = 60,
    ) -> None:
        self.chunks = chunks
        self.embedding_client = embedding_client or DeterministicEmbeddingClient()
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        *,
        sparse_top_k: int = 8,
        dense_top_k: int = 8,
        final_top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return fused hybrid retrieval results."""
        if not self.chunks:
            return []
        sparse_results = SparseRetriever(self.chunks).retrieve(query, top_k=sparse_top_k)
        dense_results = DenseRetriever(self.chunks, self.embedding_client).retrieve(
            query,
            top_k=dense_top_k,
        )
        return reciprocal_rank_fusion(
            [sparse_results, dense_results],
            k=self.rrf_k,
            top_k=final_top_k,
        )
