"""CRAG-style RAG correction agent."""

from typing import Any

from app.rag.quality.retrieval_quality_grader import RetrievalQualityGrader
from app.rag.schemas import RetrievedChunk


class RAGCorrector:
    """Bounded retrieval repair agent."""

    name = "rag_corrector"

    def __init__(
        self,
        grader: RetrievalQualityGrader | None = None,
        max_repair_attempts: int = 1,
    ) -> None:
        self.grader = grader or RetrievalQualityGrader()
        self.max_repair_attempts = max_repair_attempts

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Grade current chunks and emit repair metadata."""
        chunks = [
            RetrievedChunk.model_validate(item)
            for item in state.get("retrieved_chunks", [])
            if isinstance(item, dict)
        ]
        query = str(state.get("user_query") or "")
        grade = self.grader.grade(query, chunks)
        issues = [] if grade == "correct" else [f"retrieval_quality:{grade}"]
        return {
            "corrected_chunks": [chunk.model_dump() for chunk in chunks],
            "current_stage": self.name,
            "issues": issues,
            "rag_metrics": {
                "retrieval_quality_grade": grade,
                "repair_attempts": 0 if grade == "correct" else min(1, self.max_repair_attempts),
            },
        }
