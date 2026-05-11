"""RAG researcher agent."""

from datetime import UTC, datetime
from typing import Any

from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.schemas import ChildChunk
from app.schemas.evidence import EvidenceItem


class RAGResearcher:
    """Retrieve chunks for each research TODO and emit evidence."""

    name = "rag_researcher"

    def __init__(
        self,
        *,
        sparse_top_k: int = 8,
        dense_top_k: int = 8,
        final_top_k: int = 5,
        rrf_k: int = 60,
    ) -> None:
        self.sparse_top_k = sparse_top_k
        self.dense_top_k = dense_top_k
        self.final_top_k = final_top_k
        self.rrf_k = rrf_k

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run hybrid retrieval for all research TODOs."""
        chunks = [ChildChunk.model_validate(item) for item in state.get("rag_chunks", [])]
        retrieved: list[dict[str, Any]] = []
        evidences: list[EvidenceItem] = []
        issues: list[str] = []
        for todo in state.get("research_todos", []):
            scoped = self._scope_chunks(chunks, todo)
            results = HybridRetriever(scoped, rrf_k=self.rrf_k).retrieve(
                str(todo.get("query") or todo.get("title") or ""),
                sparse_top_k=self.sparse_top_k,
                dense_top_k=self.dense_top_k,
                final_top_k=self.final_top_k,
            )
            if not results:
                issues.append(f"rag_no_results:{todo.get('todo_id')}")
                continue
            retrieved.extend(item.model_dump() for item in results)
            evidences.extend(self._evidence_from_results(todo, results))
        competitors = self._merge_competitor_evidence(state, evidences)
        return {
            "retrieved_chunks": retrieved,
            "competitors": competitors,
            "current_stage": self.name,
            "issues": issues,
        }

    @staticmethod
    def _scope_chunks(chunks: list[ChildChunk], todo: dict[str, Any]) -> list[ChildChunk]:
        todo_id = str(todo.get("todo_id") or "")
        scoped = [chunk for chunk in chunks if chunk.todo_id == todo_id]
        if scoped:
            return scoped
        competitor = str(todo.get("competitor_name") or "")
        dimension = str(todo.get("dimension") or "")
        scoped = [
            chunk
            for chunk in chunks
            if (not competitor or chunk.competitor_name == competitor)
            and (not dimension or chunk.dimension == dimension)
        ]
        return scoped or chunks

    @staticmethod
    def _evidence_from_results(todo: dict[str, Any], results: list[Any]) -> list[EvidenceItem]:
        evidences: list[EvidenceItem] = []
        for index, result in enumerate(results, start=1):
            chunk = result.chunk
            todo_id = str(todo.get("todo_id") or "todo")
            evidence_id = f"ev_{todo_id}_{index}"
            quote = " ".join(chunk.text.split())[:200]
            evidences.append(
                EvidenceItem(
                    evidence_id=evidence_id,
                    task_id=chunk.task_id,
                    competitor_name=str(todo.get("competitor_name") or chunk.competitor_name),
                    dimension=str(todo.get("dimension") or chunk.dimension),
                    claim=f"{todo.get('dimension', 'research')} evidence"[:80],
                    value=quote[:80],
                    source_id=chunk.source_id,
                    source_url=chunk.source_url,
                    quote=quote,
                    confidence=0.65,
                    extracted_at=datetime.now(UTC).isoformat(),
                    todo_id=todo_id,
                    chunk_id=chunk.chunk_id,
                )
            )
        return evidences

    @staticmethod
    def _merge_competitor_evidence(
        state: dict[str, Any],
        evidences: list[EvidenceItem],
    ) -> list[dict[str, Any]]:
        by_name = {
            str(item.get("name")): {**item, "evidences": list(item.get("evidences", []))}
            for item in state.get("competitors", [])
            if isinstance(item, dict)
        }
        for evidence in evidences:
            item = by_name.setdefault(
                evidence.competitor_name,
                {"name": evidence.competitor_name, "sources": [], "evidences": []},
            )
            item["evidences"].append(evidence.model_dump())
        return list(by_name.values())
