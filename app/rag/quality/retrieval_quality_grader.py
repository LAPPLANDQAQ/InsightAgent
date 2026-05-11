"""CRAG-style retrieval quality grading."""

from typing import Literal

from app.rag.schemas import RetrievedChunk

RetrievalGrade = Literal["correct", "ambiguous", "incorrect"]


class RetrievalQualityGrader:
    """Grade retrieval results from the top score."""

    def __init__(self, correct_threshold: float = 0.70, ambiguous_threshold: float = 0.35) -> None:
        self.correct_threshold = correct_threshold
        self.ambiguous_threshold = ambiguous_threshold

    def grade(self, query: str, chunks: list[RetrievedChunk]) -> RetrievalGrade:
        """Return correct, ambiguous, or incorrect."""
        del query
        if not chunks:
            return "incorrect"
        top = chunks[0]
        score = top.rerank_score if top.rerank_score is not None else top.final_score
        score = top.score if score is None else score
        if score >= self.correct_threshold:
            return "correct"
        if score >= self.ambiguous_threshold:
            return "ambiguous"
        return "incorrect"
