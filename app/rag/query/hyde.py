"""Hypothetical document generation for retrieval."""

from app.rag.query.query_rewriter import LLMGenerateProtocol


class HyDEGenerator:
    """Generate deterministic hypothetical answer text."""

    def __init__(self, llm: LLMGenerateProtocol | None = None, max_chars: int = 800) -> None:
        self.llm = llm
        self.max_chars = max_chars

    async def generate(self, query: str, *, dimension: str | None = None) -> str:
        """Return a hypothetical answer for retrieval expansion."""
        if self.llm is not None:
            try:
                text = await self.llm.generate(f"Generate HyDE passage for: {query}")
                return text[: self.max_chars]
            except Exception:
                pass
        suffix = f" about {dimension}" if dimension else ""
        return (
            f"Hypothetical evidence summary{suffix}: {query}. "
            "The answer should mention official sources, concrete facts, and citations."
        )[: self.max_chars]
