"""Task summarizer agent."""

from datetime import UTC, datetime
from typing import Any

from app.schemas.research_note import ResearchNote


class TaskSummarizer:
    """Create ResearchNote records from TODO-level evidence."""

    name = "task_summarizer"

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Summarize each research TODO without mutating the input state."""
        evidences = [
            evidence
            for competitor in state.get("competitors", [])
            for evidence in competitor.get("evidences", [])
            if isinstance(evidence, dict)
        ]
        chunks: list[dict[str, Any]] = []
        for item in state.get("retrieved_chunks", []):
            if not isinstance(item, dict):
                continue
            chunk = item.get("chunk")
            chunks.append(chunk if isinstance(chunk, dict) else item)
        notes = [
            self._note_for_todo(dict(todo), evidences, chunks, str(state.get("task_id") or "task"))
            for todo in state.get("research_todos", [])
            if isinstance(todo, dict)
        ]
        return {
            "research_notes": [note.model_dump() for note in notes],
            "current_stage": self.name,
            "issues": [],
        }

    def _note_for_todo(
        self,
        todo: dict[str, Any],
        evidences: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        task_id: str,
    ) -> ResearchNote:
        matched_evidence = [item for item in evidences if self._matches(todo, item)]
        matched_chunks = [item for item in chunks if self._matches(todo, item)]
        now = datetime.now(UTC).isoformat()
        if matched_evidence:
            summary = (
                f"Found {len(matched_evidence)} evidence items for "
                f"{todo.get('competitor_name')} / {todo.get('dimension')}."
            )
            confidence = min(0.9, 0.5 + 0.1 * len(matched_evidence))
            limitations: list[str] = []
        else:
            summary = "Evidence is insufficient for this research todo."
            confidence = 0.3
            limitations = ["No valid evidence was found for this research todo."]
        return ResearchNote(
            note_id=f"note_{todo.get('todo_id', 'unknown')}",
            task_id=str(todo.get("task_id") or task_id),
            todo_id=str(todo.get("todo_id") or "unknown_todo"),
            competitor_name=str(todo.get("competitor_name") or "unknown"),
            dimension=str(todo.get("dimension") or "unknown"),
            summary=summary,
            evidence_ids=[
                str(item.get("evidence_id"))
                for item in matched_evidence
                if item.get("evidence_id")
            ],
            chunk_ids=[
                str(item.get("chunk_id"))
                for item in matched_chunks
                if item.get("chunk_id")
            ],
            source_urls=[
                str(item.get("source_url"))
                for item in matched_evidence
                if item.get("source_url")
            ],
            limitations=limitations,
            confidence=confidence,
            created_at=now,
        )

    @staticmethod
    def _matches(todo: dict[str, Any], item: dict[str, Any]) -> bool:
        if item.get("todo_id") and item.get("todo_id") == todo.get("todo_id"):
            return True
        return (
            item.get("competitor_name") == todo.get("competitor_name")
            and item.get("dimension") == todo.get("dimension")
        )
