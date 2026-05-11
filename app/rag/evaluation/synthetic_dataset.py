"""Deterministic synthetic retrieval dataset generation."""

from typing import Any

from app.rag.schemas import ChildChunk


def generate_synthetic_cases(chunks: list[ChildChunk | dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate repeatable single-hop cases from chunks."""
    parsed = [
        chunk if isinstance(chunk, ChildChunk) else ChildChunk.model_validate(chunk)
        for chunk in chunks
    ]
    cases = []
    for chunk in sorted(parsed, key=lambda item: item.chunk_id):
        subject = chunk.dimension or chunk.competitor_name or "research topic"
        cases.append(
            {
                "question": f"What evidence is available for {subject}?",
                "expected_chunk_ids": [chunk.chunk_id],
                "expected_evidence_ids": [],
                "answer_hint": chunk.text[:120],
                "difficulty": "single_hop",
            }
        )
    return cases
