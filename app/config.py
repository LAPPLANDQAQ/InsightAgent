"""Runtime settings and Qwen-only model guard."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


QWEN_MODEL_WHITELIST = frozenset(
    {
        "qwen-max",
        "qwen-plus",
        "qwen-turbo",
        "qwen-long",
        "qwen-flash",
        "qwen-max-latest",
        "qwen-plus-latest",
        "qwen-turbo-latest",
        "qwen-long-latest",
        "qwen3-max",
        "qwen3.5-plus",
        "qwen3.5-flash",
        "qwq-plus",
    }
)
FORBIDDEN_MODEL_KEYWORDS = (
    "gpt",
    "claude",
    "deepseek",
    "kimi",
    "moonshot",
    "glm",
    "yi",
    "llama",
    "ollama",
    "local",
    "mistral",
    "gemini",
)


def is_qwen_model_name(name: str) -> bool:
    """Return whether a model name is allowed for runtime LLM usage.

    Args:
        name: Raw model name from configuration.

    Returns:
        True when the name is a Qwen or QwQ runtime model.
    """
    normalized = name.strip().lower()
    if not normalized:
        return False
    if any(keyword in normalized for keyword in FORBIDDEN_MODEL_KEYWORDS):
        return False
    return normalized in QWEN_MODEL_WHITELIST or normalized.startswith(("qwen", "qwq"))


class Settings(BaseSettings):
    """Global application settings with startup validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "prod", "test"] = "dev"
    log_level: str = "INFO"

    llm_provider: Literal["qwen_dashscope"] = "qwen_dashscope"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_api_key: str = ""
    llm_heavy_model: str = "qwen-max"
    llm_light_model: str = "qwen-turbo"
    llm_fallback_model: str = "qwen-plus"
    enforce_qwen_only: bool = True

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
        """Validate that runtime LLM model settings stay within Qwen/QwQ."""
        if self.llm_provider != "qwen_dashscope":
            raise ConfigError("LLM_PROVIDER must be qwen_dashscope in runtime")
        if not self.enforce_qwen_only:
            return self
        for field_name in ("llm_heavy_model", "llm_light_model", "llm_fallback_model"):
            model_name = getattr(self, field_name)
            if not is_qwen_model_name(model_name):
                raise ConfigError(
                    f"{field_name}={model_name!r} is not allowed. "
                    "Runtime models must be Qwen/QwQ only."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached global settings instance."""
    return Settings()
