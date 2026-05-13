"""File size limit tests."""

from pathlib import Path

MAX_LINES = 300
WHITELIST = {"app/config.py", "app/infra/llm/deepseek_client.py"}


def test_file_size():
    for py_file in Path("app").rglob("*.py"):
        rel_path = str(py_file).replace("\\", "/")
        if rel_path in WHITELIST:
            continue
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        assert lines <= MAX_LINES, f"{py_file} has {lines} lines (max {MAX_LINES})"
