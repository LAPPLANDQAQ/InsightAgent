"""Runtime settings and DeepSeek model guards."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


DEEPSEEK_MODEL_WHITELIST = frozenset(
    {
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "deepseek-chat",
        "deepseek-reasoner",
    }
)
DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"


def is_deepseek_model_name(name: str) -> bool:
    """Return whether a model name is allowed for DeepSeek runtime usage.

    Args:
        name: Raw model name from configuration.

    Returns:
        True when the name is a supported DeepSeek hosted API model.
    """
    normalized = name.strip().lower()
    return normalized in DEEPSEEK_MODEL_WHITELIST


class Settings(BaseSettings):
    """Global application settings with startup validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "prod", "test"] = "dev"
    log_level: str = "INFO"

    llm_provider: Literal["deepseek"] = "deepseek"
    llm_base_url: str = DEEPSEEK_DEFAULT_BASE_URL
    deepseek_api_key: str = ""
    llm_heavy_model: str = "deepseek-v4-pro"
    llm_light_model: str = "deepseek-v4-flash"
    llm_fallback_model: str = "deepseek-v4-flash"
    enforce_provider_model_guard: bool = True

    search_providers: str = "tavily,duckduckgo"
    tavily_api_key: str = ""

    cache_backend: Literal["sqlite", "memory"] = "sqlite"
    db_url: str = "sqlite:///./data/insight.db"
    mysql_url: str = ""

    max_concurrent_search: int = Field(default=5, ge=1, le=20)
    max_concurrent_fetch: int = Field(default=8, ge=1, le=30)
    max_concurrent_llm_heavy: int = Field(default=2, ge=1, le=5)
    max_concurrent_llm_light: int = Field(default=5, ge=1, le=20)

    max_iterations: int = Field(default=3, ge=1, le=5)
    max_search_rounds_per_competitor: int = Field(default=3, ge=1, le=6)
    sufficiency_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    enable_llm_critic: bool = False

    max_heavy_calls_per_task: int = Field(default=8, ge=1, le=20)
    max_heavy_tokens_per_task: int = Field(default=35000, ge=1000)
    max_light_tokens_per_task: int = Field(default=100000, ge=1000)

    @model_validator(mode="after")
    def validate_runtime_models(self) -> "Settings":
        """Validate runtime LLM model settings for DeepSeek."""
        if not self.enforce_provider_model_guard:
            return self
        for field_name in ("llm_heavy_model", "llm_light_model", "llm_fallback_model"):
            model_name = getattr(self, field_name)
            if not is_deepseek_model_name(model_name):
                raise ConfigError(
                    f"{field_name}={model_name!r} is not allowed. "
                    "Runtime models must match provider DeepSeek."
                )
        return self

    @property
    def llm_api_key(self) -> str:
        """Return the API key for DeepSeek."""
        return self.deepseek_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached global settings instance."""
    return Settings()
