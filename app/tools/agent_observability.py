"""Agent-safe observability helpers."""

from logging import Logger

from app.infra.logger import get_logger
from app.infra.security.redaction import redact_secret_like


def get_agent_logger(name: str) -> Logger:
    """Return a logger for an agent module."""
    return get_logger(name)


def redact_issue(message: str) -> str:
    """Redact secret-like values from user-visible issue text."""
    return redact_secret_like(message)
