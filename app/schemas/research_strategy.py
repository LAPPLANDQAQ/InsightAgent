"""Research strategy data contract."""

from typing import Literal

from pydantic import BaseModel, Field

ResearchRoute = Literal["pricing", "docs", "github", "news", "default"]


class ResearchStrategy(BaseModel):
    """Retrieval and source preferences for one research TODO."""

    todo_id: str = Field(min_length=1)
    route: ResearchRoute = "default"
    search_query: str = Field(min_length=1)
    preferred_source_types: list[str] = Field(default_factory=list)
    sparse_top_k: int = Field(default=8, ge=1)
    dense_top_k: int = Field(default=8, ge=1)
    final_top_k: int = Field(default=5, ge=1)
    freshness_required: bool = False
