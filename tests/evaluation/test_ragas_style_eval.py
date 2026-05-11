"""Tests for RAGAs-style local evaluation."""

from app.rag.evaluation.ragas_style import build_report, evaluate_case


def test_ragas_style_report_shape():
    """RAGAs-style report includes summary, cases, generated_at, and notes."""
    case = {
        "question": "Cursor pricing",
        "answer": "Cursor pricing [ev_1]",
        "evidences": [{"evidence_id": "ev_1"}],
        "expected_chunk_ids": ["chunk_1"],
        "retrieved_chunk_ids": ["chunk_1"],
    }

    assert evaluate_case(case)["citation_validity"] == 1.0
    report = build_report([case])
    assert {"summary", "cases", "generated_at", "notes"} <= set(report)
