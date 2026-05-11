"""Tests for RAG evaluation helpers."""

from app.rag.evaluation.citation_metrics import citation_validity
from app.rag.evaluation.ragas_style import build_report
from app.rag.evaluation.report_quality import dimension_coverage
from app.rag.evaluation.retrieval_metrics import hit_at_k, mean_reciprocal_rank, ndcg_at_k
from app.rag.evaluation.synthetic_dataset import generate_synthetic_cases
from app.rag.schemas import ChildChunk


def test_retrieval_metrics():
    ranked = ["a", "b", "c"]
    relevant = {"b"}

    assert hit_at_k(ranked, relevant, 2) == 1.0
    assert mean_reciprocal_rank(ranked, relevant) == 0.5
    assert ndcg_at_k(ranked, relevant, 3) > 0


def test_citation_and_dimension_metrics():
    citation = citation_validity("Claim [ev_1] [ev_missing]", [{"evidence_id": "ev_1"}])
    coverage = dimension_coverage(
        "pricing features".split(),
        [{"dimension": "pricing", "confidence": 0.8}],
    )

    assert citation["score"] == 0.5
    assert coverage["missing_dimensions"] == ["features"]


def test_synthetic_dataset_and_ragas_report():
    chunk = ChildChunk(
        chunk_id="chunk_1",
        parent_doc_id="parent_1",
        task_id="task_1",
        source_id="src_1",
        source_url="https://example.com",
        text="Cursor pricing evidence",
        chunk_index=0,
    )

    cases = generate_synthetic_cases([chunk])
    report = build_report(
        [
            {
                "question": cases[0]["question"],
                "answer": "Cursor pricing evidence [ev_1]",
                "evidences": [{"evidence_id": "ev_1"}],
                "expected_chunk_ids": ["chunk_1"],
                "retrieved_chunk_ids": ["chunk_1"],
            }
        ]
    )

    assert cases[0]["expected_chunk_ids"] == ["chunk_1"]
    assert report["summary"]["context_precision"] == 1.0
