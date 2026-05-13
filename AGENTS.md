# Repository Guidelines

## Project Structure & Module Organization

InsightAgent is a Python 3.12 FastAPI + LangGraph + Streamlit project. Core backend code lives in `app/`, organized by layer: `api`, `services`, `graph`, `agents`, `tools`, `rag`, `harness`, `mcp_server`, and `infra`. Streamlit UI code is in `frontend/`. Tests are under `tests/`, with focused suites such as `tests/unit`, `tests/integration`, `tests/architecture`, `tests/mcp`, and `tests/harness`. Local examples and utility scripts live in `examples/` and `scripts/`; documentation is in `docs/`.

## Build, Test, and Development Commands

Install with development tools:

```bash
pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the Streamlit dashboard:

```bash
streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=127.0.0.1
```

Use these checks before submitting changes:

```bash
python -m compileall app frontend
python -m ruff check app tests examples scripts frontend
python -m mypy app --ignore-missing-imports
python -m pytest tests -q
```

## Coding Style & Naming Conventions

Use 4-space indentation and Python type hints for public interfaces. Ruff enforces import order, common lint rules, and a 100-character line length. Keep modules small; architecture tests enforce file-size limits. Follow existing naming patterns: snake_case for functions and variables, PascalCase for Pydantic models and classes, and explicit test names like `test_cancel_unknown_task_returns_404`.

## Testing Guidelines

Tests use `pytest` and `pytest-asyncio`. Add regression tests for behavior changes, especially API responses, workflow routing, tools, frontend helpers, and security redaction. Tests must not call real LLM APIs, search APIs, web pages, LangFuse services, or MCP clients. Use fakes, stubs, and `httpx.MockTransport`.

## Commit & Pull Request Guidelines

History uses concise conventional-style subjects, for example `fix: harden v4.0.2 release path` and `feat(frontend): redesign Streamlit interface`. Keep commits focused on one logical change. Pull requests should summarize behavior changes, list validation commands run, note config or docs updates, and include screenshots only for visible UI changes.

## Security & Architecture Notes

Runtime LLM support is DeepSeek-only; the OpenAI SDK is only a DeepSeek-compatible transport. Agents orchestrate only and must not directly call SDKs, HTTP clients, databases, or filesystem side effects. Stable local defaults are SQLite, Streamlit, and safe MCP behavior.
