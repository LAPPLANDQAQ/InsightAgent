"""Runtime settings and provider model guards."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
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
DEEPSEEK_MODEL_WHITELIST = frozenset(
    {
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "deepseek-chat",
        "deepseek-reasoner",
    }
)
QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"


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

    llm_provider: Literal["qwen_dashscope", "deepseek"] = "deepseek"
    llm_base_url: str = DEEPSEEK_DEFAULT_BASE_URL
    dashscope_api_key: str = ""
    deepseek_api_key: str = ""
    llm_heavy_model: str = "deepseek-v4-pro"
    llm_light_model: str = "deepseek-v4-flash"
    llm_fallback_model: str = "deepseek-v4-flash"
    enforce_provider_model_guard: bool = Field(
        default=True,
        validation_alias=AliasChoices("ENFORCE_PROVIDER_MODEL_GUARD", "ENFORCE_QWEN_ONLY"),
    )

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
        """Validate runtime LLM model settings for the selected provider."""
        if self.llm_provider == "deepseek" and self.llm_base_url == QWEN_DEFAULT_BASE_URL:
            self.llm_base_url = DEEPSEEK_DEFAULT_BASE_URL
        if self.llm_provider == "qwen_dashscope" and self.llm_base_url == DEEPSEEK_DEFAULT_BASE_URL:
            self.llm_base_url = QWEN_DEFAULT_BASE_URL
        if not self.enforce_provider_model_guard:
            return self
        validator = (
            is_qwen_model_name if self.llm_provider == "qwen_dashscope" else is_deepseek_model_name
        )
        provider_name = "Qwen/QwQ" if self.llm_provider == "qwen_dashscope" else "DeepSeek"
        for field_name in ("llm_heavy_model", "llm_light_model", "llm_fallback_model"):
            model_name = getattr(self, field_name)
            if not validator(model_name):
                raise ConfigError(
                    f"{field_name}={model_name!r} is not allowed. "
                    f"Runtime models must match provider {provider_name}."
                )
        return self

    @property
    def llm_api_key(self) -> str:
        """Return the API key for the selected LLM provider."""
        if self.llm_provider == "deepseek":
            return self.deepseek_api_key
        return self.dashscope_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached global settings instance."""
    return Settings()
