"""Structured logger tests."""

import json
import logging

from app.infra.logger import JsonFormatter


def test_json_formatter_includes_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="task_started",
        args=(),
        exc_info=None,
    )
    record.task_id = "task_1"
    payload = json.loads(formatter.format(record))
    assert payload["message"] == "task_started"
    assert payload["task_id"] == "task_1"
