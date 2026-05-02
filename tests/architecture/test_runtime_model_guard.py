"""Runtime model guard architecture tests."""

import pytest

from app.config import QWEN_MODEL_WHITELIST, Settings, is_qwen_model_name


@pytest.fixture
def base_env(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "fake_key")
    monkeypatch.setenv("LLM_PROVIDER", "qwen_dashscope")
    monkeypatch.setenv("ENFORCE_QWEN_ONLY", "true")


def test_settings_reject_gpt(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "gpt-5.5")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "qwen-turbo")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    with pytest.raises(Exception, match="Qwen"):
        Settings()


def test_settings_reject_claude(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen-max")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "claude-3-haiku")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    with pytest.raises(Exception, match="Qwen"):
        Settings()


def test_settings_reject_deepseek(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen-max")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    with pytest.raises(Exception, match="Qwen"):
        Settings()


def test_settings_accept_qwen(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen-max")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "qwen-turbo")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    settings = Settings()
    assert settings.llm_heavy_model == "qwen-max"


def test_settings_accept_new_qwen_prefix(base_env, monkeypatch):
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen3.5-plus")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "qwen3.5-flash")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwq-plus")
    settings = Settings()
    assert settings.llm_light_model == "qwen3.5-flash"


def test_whitelist_completeness():
    assert "qwen-max" in QWEN_MODEL_WHITELIST
    assert "qwen-turbo" in QWEN_MODEL_WHITELIST
    assert "qwen-plus" in QWEN_MODEL_WHITELIST
    assert is_qwen_model_name("qwen-max-latest")
