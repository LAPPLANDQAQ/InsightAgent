"""RAG indexing agent."""

from typing import Any

from app.rag.chunkers.parent_child_chunker import ParentChildChunker
from app.rag.cleaners.text_cleaner import TextCleaner


class RAGIndexer:
    """Clean source text and split it into RAG chunks."""

    name = "rag_indexer"

    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        self.cleaner = TextCleaner()
        self.chunker = ParentChildChunker(chunk_size=chunk_size, overlap=overlap)

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Index fetched pages or evidence snippets already present in state."""
        task_id = str(state.get("task_id") or "task")
        pages = self._source_pages(state)
        parents: list[dict[str, Any]] = []
        chunks: list[dict[str, Any]] = []
        issues: list[str] = []
        for index, page in enumerate(pages, start=1):
            text = self.cleaner.clean(str(page.get("text") or ""))
            if not text:
                issues.append(f"rag_index_empty:{page.get('source_id') or index}")
                continue
            result = self.chunker.chunk_document(
                task_id=task_id,
                source_id=str(page.get("source_id") or f"src_{index}"),
                source_url=str(page.get("source_url") or page.get("url") or "unknown"),
                title=str(page.get("title") or ""),
                text=text,
                todo_id=page.get("todo_id"),
                competitor_name=page.get("competitor_name"),
                dimension=page.get("dimension"),
                source_type=str(page.get("source_type") or "unknown"),
                metadata={"origin": str(page.get("origin") or "state")},
            )
            parents.append(result.parent.model_dump())
            chunks.extend(chunk.model_dump() for chunk in result.chunks)
        return {
            "rag_parent_docs": parents,
            "rag_chunks": chunks,
            "current_stage": self.name,
            "issues": issues,
        }

    def _source_pages(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        pages = [item for item in state.get("fetched_pages", []) if isinstance(item, dict)]
        if pages:
            return pages
        evidence_pages: list[dict[str, Any]] = []
        for competitor in state.get("competitors", []):
            for evidence in competitor.get("evidences", []):
                evidence_pages.append(
                    {
                        "source_id": evidence.get("source_id"),
                        "source_url": evidence.get("source_url"),
                        "text": evidence.get("quote") or evidence.get("value"),
                        "competitor_name": evidence.get("competitor_name"),
                        "dimension": evidence.get("dimension"),
                        "todo_id": evidence.get("todo_id"),
                        "origin": "evidence",
                    }
                )
        return evidence_pages
