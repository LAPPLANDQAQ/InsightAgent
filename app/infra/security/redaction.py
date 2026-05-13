"""Secret redaction helpers."""

import re

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)=([^,\s\]\)'\"]+)"
)
AUTHORIZATION_BEARER_RE = re.compile(r"(?i)(Authorization:\s*Bearer\s+)([^\s,\]\)'\"]+)")
BARE_BEARER_RE = re.compile(r"(?i)\bBearer\s+([^\s,\]\)'\"]+)")
SECRET_TOKEN_RE = re.compile(r"\b(?:sk|tvly)-[A-Za-z0-9._-]+")


def redact_secret_like(text: str) -> str:
    """Redact secret-looking values from diagnostic text."""
    redacted = SECRET_ASSIGNMENT_RE.sub(r"\1=[REDACTED]", text)
    redacted = AUTHORIZATION_BEARER_RE.sub(r"\1[REDACTED]", redacted)
    redacted = BARE_BEARER_RE.sub("Bearer [REDACTED]", redacted)
    return SECRET_TOKEN_RE.sub("[REDACTED]", redacted)
