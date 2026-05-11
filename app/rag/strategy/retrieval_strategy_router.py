"""Adaptive retrieval strategy router."""

from pydantic import BaseModel, Field, model_validator


class RetrievalStrategyConfig(BaseModel):
    """Retriever weights and limits for one dimension."""

    strategy_name: str
    sparse_weight: float = Field(ge=0.0, le=1.0)
    dense_weight: float = Field(ge=0.0, le=1.0)
    sparse_top_k: int = Field(ge=1)
    dense_top_k: int = Field(ge=1)
    final_top_k: int = Field(ge=1)
    enable_hyde: bool = False
    enable_query_rewrite: bool = False
    freshness_hint: bool = False

    @model_validator(mode="after")
    def validate_weights(self) -> "RetrievalStrategyConfig":
        """Validate that at least one retriever has weight."""
        if self.sparse_weight + self.dense_weight <= 0:
            raise ValueError("at least one retrieval weight must be positive")
        return self


class RetrievalStrategyRouter:
    """Route research dimensions to retrieval settings."""

    def route(self, dimension: str | None, query: str | None = None) -> RetrievalStrategyConfig:
        """Return retrieval settings for a dimension and query."""
        text = f"{dimension or ''} {query or ''}".lower()
        if any(term in text for term in ("pricing", "cost", "plan", "billing")):
            return self._config("pricing_sparse", 0.75, 0.25)
        if any(term in text for term in ("architecture", "technical", "implementation")):
            return self._config("technical_dense", 0.35, 0.65)
        if any(term in text for term in ("risk", "news", "policy", "security")):
            return self._config("freshness_hybrid", 0.5, 0.5, freshness=True)
        if any(term in text for term in ("features", "capability", "docs", "ecosystem")):
            return self._config("balanced_docs", 0.5, 0.5, rewrite=True)
        return self._config("balanced_default", 0.5, 0.5)

    @staticmethod
    def _config(
        name: str,
        sparse: float,
        dense: float,
        *,
        freshness: bool = False,
        rewrite: bool = False,
    ) -> RetrievalStrategyConfig:
        return RetrievalStrategyConfig(
            strategy_name=name,
            sparse_weight=sparse,
            dense_weight=dense,
            sparse_top_k=8,
            dense_top_k=8,
            final_top_k=5,
            enable_query_rewrite=rewrite,
            freshness_hint=freshness,
        )
