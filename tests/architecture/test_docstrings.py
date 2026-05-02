"""Public function docstring tests."""

import ast
from pathlib import Path


def test_public_functions_have_docstrings():
    for py_file in Path("app").rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("_"):
                    continue
                assert ast.get_docstring(node), f"{py_file}::{node.name} missing docstring"
