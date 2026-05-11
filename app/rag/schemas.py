"""Core RAG document and retrieval schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ParentDocument(BaseModel):
    """Clean source document that owns retrievable child chunks."""

    parent_doc_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    todo_id: str | None = None
    source_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    title: str = ""
    text: str = Field(min_length=1)
    source_type: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ChildChunk(BaseModel):
    """Searchable child chunk with parent document context."""

    chunk_id: str = Field(min_length=1)
    parent_doc_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    todo_id: str | None = None
    source_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    competitor_name: str | None = None
    dimension: str | None = None
    text: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    token_count: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """Chunk returned by a retriever with ranking metadata."""

    chunk: ChildChunk
    retriever_name: str = Field(min_length=1)
    rank: int = Field(ge=1)
    score: float = 0.0
    final_score: float | None = None
    rerank_score: float | None = None
    matched_terms: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
