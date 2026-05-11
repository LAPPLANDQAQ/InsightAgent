"""Dense retriever using an injectable embedding client."""

from app.rag.index.embedding_client import EmbeddingClientProtocol, cosine_similarity
from app.rag.schemas import ChildChunk, RetrievedChunk


class DenseRetriever:
    """Retrieve chunks by deterministic cosine similarity."""

    name = "dense"

    def __init__(self, chunks: list[ChildChunk], embedding_client: EmbeddingClientProtocol) -> None:
        self.chunks = chunks
        self.embedding_client = embedding_client

    def retrieve(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        """Return top dense matches for query."""
        if not query.strip() or not self.chunks:
            return []
        vectors = self.embedding_client.embed([query] + [chunk.text for chunk in self.chunks])
        query_vector = vectors[0]
        scored = [
            (cosine_similarity(query_vector, vector), chunk)
            for vector, chunk in zip(vectors[1:], self.chunks, strict=True)
        ]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            RetrievedChunk(
                chunk=chunk,
                retriever_name=self.name,
                rank=index,
                score=float(score),
            )
            for index, (score, chunk) in enumerate(scored[:top_k], start=1)
        ]
