"""RAGAs-style deterministic evaluation."""

from typing import Any, Protocol

from app.rag.evaluation.citation_metrics import citation_validity


class JudgeClientProtocol(Protocol):
    """Protocol for optional judge clients."""

    async def judge(self, prompt: str, **kwargs: object) -> dict[str, Any] | str:
        """Return judge output for a prompt."""
        ...


class FakeJudge:
    """Deterministic judge used by tests."""

    async def judge(self, prompt: str, **kwargs: object) -> dict[str, Any]:
        """Return stable scores without external APIs."""
        del prompt, kwargs
        return {"faithfulness": 0.8, "answer_relevance": 0.8, "context_precision": 0.8}


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one RAG case with rule-based metrics."""
    report = str(case.get("answer") or case.get("report") or "")
    evidences = list(case.get("evidences") or [])
    citation = citation_validity(report, evidences)
    expected_chunks = set(case.get("expected_chunk_ids") or [])
    retrieved_chunks = set(case.get("retrieved_chunk_ids") or [])
    overlap = len(expected_chunks & retrieved_chunks)
    context_precision = 1.0 if not expected_chunks else overlap / len(expected_chunks)
    relevance = _token_overlap(str(case.get("question") or ""), report)
    return {
        "faithfulness": citation["score"],
        "answer_relevance": relevance,
        "context_precision": context_precision,
        "citation_validity": citation["score"],
    }


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a JSON-serializable aggregate report."""
    evaluated = [{**case, "scores": evaluate_case(case)} for case in cases]
    summary: dict[str, float] = {}
    for key in ("faithfulness", "answer_relevance", "context_precision", "citation_validity"):
        values = [item["scores"][key] for item in evaluated]
        summary[key] = 0.0 if not values else sum(values) / len(values)
    return {"summary": summary, "cases": evaluated, "notes": ["rule_based_no_external_api"]}


def _token_overlap(question: str, answer: str) -> float:
    q_tokens = set(question.lower().split())
    if not q_tokens:
        return 0.0
    return len(q_tokens & set(answer.lower().split())) / len(q_tokens)
