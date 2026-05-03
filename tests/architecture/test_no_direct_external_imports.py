"""Tests for forbidden direct runtime imports."""

import ast
from pathlib import Path

FORBIDDEN_BASE = {"anthropic", "deepseek"}
FORBIDDEN_IN_AGENTS = {
    "httpx",
    "openai",
    "anthropic",
    "duckduckgo_search",
    "tavily",
}
RUNTIME_DIRS = ["agents", "graph", "services", "api"]
APP_ROOT = Path("app")
LLM_PROTOCOL_IMPORT = "app.infra.llm.base"


def _iter_imports(py_file: Path):
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_runtime_not_import_forbidden_sdk():
    for dir_name in RUNTIME_DIRS:
        for py_file in (APP_ROOT / dir_name).rglob("*.py"):
            for name in _iter_imports(py_file):
                base = name.split(".")[0].lower()
                assert base not in FORBIDDEN_BASE, f"{py_file} imports forbidden SDK: {name}"


def test_openai_sdk_only_used_by_deepseek_client():
    allowed = APP_ROOT / "infra" / "llm" / "deepseek_client.py"
    for py_file in APP_ROOT.rglob("*.py"):
        for name in _iter_imports(py_file):
            if name.split(".")[0].lower() == "openai":
                assert py_file == allowed, (
                    f"openai SDK only allowed in {allowed}, found in {py_file}"
                )


def test_agents_not_import_external_libs():
    for py_file in (APP_ROOT / "agents").rglob("*.py"):
        for name in _iter_imports(py_file):
            base = name.split(".")[0].lower()
            assert base not in FORBIDDEN_IN_AGENTS, f"{py_file} imports forbidden lib: {name}"


def test_agents_not_import_infra_implementations():
    for py_file in (APP_ROOT / "agents").rglob("*.py"):
        for name in _iter_imports(py_file):
            if name == LLM_PROTOCOL_IMPORT:
                continue
            assert not name.startswith("app.infra"), (
                f"{py_file} imports infra implementation: {name}"
            )


def test_tools_not_import_each_other():
    tools_dir = APP_ROOT / "tools"
    for py_file in tools_dir.rglob("*.py"):
        if py_file.name in {"__init__.py", "dedup.py"}:
            continue
        for name in _iter_imports(py_file):
            if name.startswith("app.tools.") and name != "app.tools.dedup":
                raise AssertionError(f"{py_file} imports another tool: {name}")
