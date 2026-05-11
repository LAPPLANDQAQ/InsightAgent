"""Research note data contract."""

from pydantic import BaseModel, Field


class ResearchNote(BaseModel):
    """Intermediate summary for one research TODO."""

    note_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    todo_id: str = Field(min_length=1)
    competitor_name: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: str
