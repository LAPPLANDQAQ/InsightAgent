"""Layer dependency direction tests."""

import ast
from pathlib import Path

APP_ROOT = Path("app")


def _imports_of(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_infra_not_import_upper_layers():
    for py_file in (APP_ROOT / "infra").rglob("*.py"):
        for name in _imports_of(py_file):
            for forbidden in ("app.agents", "app.graph", "app.services", "app.api"):
                assert not name.startswith(forbidden), f"{py_file} imports upper layer: {name}"


def test_tools_not_import_upper_layers():
    for py_file in (APP_ROOT / "tools").rglob("*.py"):
        for name in _imports_of(py_file):
            for forbidden in ("app.agents", "app.graph", "app.services", "app.api"):
                assert not name.startswith(forbidden), f"{py_file} imports upper layer: {name}"
