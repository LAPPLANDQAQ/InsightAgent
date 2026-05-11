"""Query rewriting helpers."""

from typing import Protocol


class LLMGenerateProtocol(Protocol):
    """Protocol for simple async text generation."""

    async def generate(self, prompt: str, **kwargs: object) -> str:
        """Generate text from a prompt."""
        ...


class QueryRewriter:
    """Create deterministic retrieval query variants."""

    def __init__(self, llm: LLMGenerateProtocol | None = None) -> None:
        self.llm = llm

    def rewrite(
        self,
        query: str,
        *,
        dimension: str | None = None,
        competitor_name: str | None = None,
    ) -> list[str]:
        """Return original query plus rule-based variants."""
        base = query.strip()
        variants = [base] if base else []
        if competitor_name and dimension:
            variants.append(f"{competitor_name} {dimension} official documentation")
        if dimension:
            variants.append(f"{dimension} pricing features docs")
        return _dedupe(variants)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.lower()
        if key and key not in seen:
            seen.add(key)
            output.append(value)
    return output
