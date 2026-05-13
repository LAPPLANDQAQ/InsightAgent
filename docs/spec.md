# InsightAgent Stable Local Scope

This repository is scoped as a local, interview-ready AI agent project.

The stable runtime is intentionally narrow:

- FastAPI task API and health check.
- Streamlit local demo UI.
- LangGraph multi-agent research workflow.
- DeepSeek-only LLM runtime.
- SQLite default persistence and cache.
- Safe fetch/search abstractions with deterministic tests.
- Read-only MCP adapter by default.
- Local evaluation metrics without unverified measured claims.

Historical upgrade prompts and one-off review logs have been removed from the active docs set. Current
architecture, RAG, harness, MCP, evaluation, stable release notes, and deferred items are documented in
the focused files under `docs/`.
