"""Research plan data contracts."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.research_todo import ResearchTodo


class ResearchPlan(BaseModel):
    """Planner output describing the research scope."""

    market: str
    competitors: list[str] = Field(min_length=2, max_length=6)
    dimensions: list[str] = Field(min_length=3, max_length=8)
    search_queries: dict[str, list[str]]
    required_fields: dict[str, list[str]]
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    research_todos: list[ResearchTodo] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_required_fields_match_dimensions(self) -> "ResearchPlan":
        """Validate required field keys match dimensions exactly.

        Returns:
            The validated research plan.

        Raises:
            ValueError: Raised when required_fields does not cover every dimension.
        """
        if set(self.required_fields) != set(self.dimensions):
            raise ValueError(
                "required_fields keys must match dimensions exactly. "
                f"dimensions={self.dimensions}, "
                f"required_fields_keys={list(self.required_fields)}"
            )
        return self
