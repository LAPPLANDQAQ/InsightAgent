"""Secret redaction tests."""

from app.infra.security.redaction import redact_secret_like


def test_redact_secret_like_patterns():
    text = (
        "api_key=abc123 token=def456 secret=ghi789 password=jkl "
        "Authorization: Bearer bearer-token tvly-test sk-test"
    )

    redacted = redact_secret_like(text)

    assert "api_key=[REDACTED]" in redacted
    assert "token=[REDACTED]" in redacted
    assert "secret=[REDACTED]" in redacted
    assert "password=[REDACTED]" in redacted
    assert "Authorization: Bearer [REDACTED]" in redacted
    assert "[REDACTED]" in redacted
    assert "abc123" not in redacted
    assert "def456" not in redacted
    assert "ghi789" not in redacted
    assert "jkl" not in redacted
    assert "bearer-token" not in redacted
    assert "tvly-test" not in redacted
    assert "sk-test" not in redacted
