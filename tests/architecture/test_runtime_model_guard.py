"""Runtime model guard architecture tests."""

import pytest

from app.config import (
    DEEPSEEK_MODEL_WHITELIST,
    Settings,
    is_deepseek_model_name,
)


@pytest.fixture
def base_env(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake_key")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("ENFORCE_PROVIDER_MODEL_GUARD", "true")


def test_settings_reject_gpt(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "gpt-5.5")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "deepseek-v4-flash")
    with pytest.raises(Exception, match="DeepSeek"):
        Settings()


def test_settings_reject_claude(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "claude-3-haiku")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "deepseek-v4-flash")
    with pytest.raises(Exception, match="DeepSeek"):
        Settings()


def test_settings_reject_non_hosted_deepseek_model(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "deepseek-local")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "deepseek-v4-flash")
    with pytest.raises(Exception, match="DeepSeek"):
        Settings()


def test_settings_accept_deepseek_defaults(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "deepseek-v4-flash")
    settings = Settings()
    assert settings.llm_api_key == "fake_key"
    assert settings.llm_heavy_model == "deepseek-v4-pro"


def test_whitelist_completeness():
    assert "deepseek-v4-flash" in DEEPSEEK_MODEL_WHITELIST
    assert "deepseek-v4-pro" in DEEPSEEK_MODEL_WHITELIST
    assert is_deepseek_model_name("deepseek-v4-flash")
