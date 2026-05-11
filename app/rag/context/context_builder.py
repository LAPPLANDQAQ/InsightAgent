"""Build bounded retrieval context strings."""

from app.rag.schemas import RetrievedChunk


class ContextBuilder:
    """Render retrieved chunks into citation-friendly context."""

    def build(self, chunks: list[RetrievedChunk], max_chars: int = 4000) -> str:
        """Return a ranked context string capped by max_chars."""
        rendered: list[str] = []
        total = 0
        for item in sorted(chunks, key=lambda chunk: chunk.rank):
            header = (
                f"[{item.chunk.chunk_id}] source={item.chunk.source_url} "
                f"rank={item.rank} score={item.score:.3f}\n"
            )
            body = item.chunk.text.strip()
            segment = f"{header}{body}"
            if total + len(segment) > max_chars:
                remaining = max_chars - total
                if remaining > len(header):
                    rendered.append(segment[:remaining].rstrip())
                break
            rendered.append(segment)
            total += len(segment)
        return "\n\n".join(rendered)
