"""Tests for synthetic dataset generation."""

from app.rag.evaluation.synthetic_dataset import generate_synthetic_cases
from app.rag.schemas import ChildChunk


def test_synthetic_dataset_generation_is_repeatable():
    """Synthetic cases are sorted by chunk id and repeatable."""
    chunk = ChildChunk(
        chunk_id="chunk_b",
        parent_doc_id="parent",
        task_id="task",
        source_id="src",
        source_url="https://example.com",
        text="Evidence text",
        chunk_index=0,
    )

    first = generate_synthetic_cases([chunk])
    second = generate_synthetic_cases([chunk.model_dump()])
    assert first == second
    assert first[0]["difficulty"] == "single_hop"
