"""Parent-child chunking utilities."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.rag.schemas import ChildChunk, ParentDocument


@dataclass(frozen=True)
class ChunkingResult:
    """Parent document and generated child chunks."""

    parent: ParentDocument
    chunks: list[ChildChunk]


class ParentChildChunker:
    """Split cleaned documents into stable overlapping child chunks."""

    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = min(overlap, max(chunk_size - 1, 0))

    def chunk_document(
        self,
        *,
        task_id: str,
        source_id: str,
        source_url: str,
        title: str,
        text: str,
        todo_id: str | None = None,
        competitor_name: str | None = None,
        dimension: str | None = None,
        source_type: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> ChunkingResult:
        """Create one parent document and its child chunks."""
        safe_source = self._safe(source_id)
        parent_id = f"parent_{self._safe(task_id)}_{safe_source}"
        parent = ParentDocument(
            parent_doc_id=parent_id,
            task_id=task_id,
            todo_id=todo_id,
            source_id=source_id,
            source_url=source_url,
            title=title,
            text=text,
            source_type=source_type,
            metadata=metadata or {},
            created_at=datetime.now(UTC).isoformat(),
        )
        chunks = [
            ChildChunk(
                chunk_id=f"chunk_{parent_id}_{index}",
                parent_doc_id=parent_id,
                task_id=task_id,
                todo_id=todo_id,
                source_id=source_id,
                source_url=source_url,
                competitor_name=competitor_name,
                dimension=dimension,
                text=chunk_text,
                chunk_index=index,
                token_count=len(chunk_text.split()),
                metadata=metadata or {},
            )
            for index, chunk_text in enumerate(self._windows(text))
        ]
        return ChunkingResult(parent=parent, chunks=chunks)

    def _windows(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        chunks: list[str] = []
        start = 0
        while start < len(text):
            part = text[start : start + self.chunk_size].strip()
            if part:
                chunks.append(part)
            if start + self.chunk_size >= len(text):
                break
            start += self.chunk_size - self.overlap
        return chunks

    @staticmethod
    def _safe(value: str) -> str:
        return "".join(char if char.isalnum() else "_" for char in value).strip("_") or "item"
