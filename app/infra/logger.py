"""Structured logging helpers."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as one-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record.

        Args:
            record: Python logging record.

        Returns:
            JSON-encoded log line.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in logging.LogRecord("", 0, "", 0, "", (), None).__dict__:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logger(level: str = "INFO") -> logging.Logger:
    """Configure root logging for structured output.

    Args:
        level: Logging level name.

    Returns:
        Configured root logger.
    """
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Logger name.

    Returns:
        Named logger.
    """
    return logging.getLogger(name)
