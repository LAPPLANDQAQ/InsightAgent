"""Source data contracts."""

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["official", "media", "community", "review", "paper", "unknown"]


class SourceItem(BaseModel):
    """Single information source."""

    source_id: str
    url: str
    domain: str
    title: str
    source_type: SourceType
    credibility_score: float = Field(ge=0.0, le=1.0)
    classification_method: Literal["rule", "llm", "fallback"]
    published_at: str | None = None
    retrieved_at: str
