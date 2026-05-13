"""Configuration security tests."""

from app.config import Settings


def test_settings_model_dump_excludes_secret_values():
    settings = Settings(
        deepseek_api_key="sk-test",
        tavily_api_key="tvly-test",
        mcp_http_auth_token="secret-token",
    )

    dumped = str(settings.model_dump())
    represented = repr(settings)

    assert "sk-test" not in dumped
    assert "tvly-test" not in dumped
    assert "secret-token" not in dumped
    assert "sk-test" not in represented
    assert "tvly-test" not in represented
    assert "secret-token" not in represented
