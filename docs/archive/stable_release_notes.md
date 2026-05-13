# Stable Release Notes

## Project Scope

InsightAgent v4 is a local TODO-driven RAG research agent for competitive and public-source analysis.
The stable release keeps the runtime DeepSeek-only, SQLite-based by default, and safe to demonstrate
without adding new platform or provider scope.

## Stability Fixes Completed

- Task lifecycle exposes queued, running, failed, and completed states through the API.
- Stale persisted `RUNNING` tasks are marked failed on startup or status read.
- Task persistence rolls back on failed result writes.
- In-memory task, cache, trace, and policy state use bounded concurrency controls.
- Harness tool call slots are checked and recorded atomically through `PolicyEngine.acquire_slot()`.
- LLM transient failures retry and fall back only to configured DeepSeek models.
- Generic LLM error diagnostics redact secret-like values before surfacing errors.
- Fetching blocks local/private hosts, unsafe schemes, unsafe DNS results, oversized responses,
  unsupported content types, and redirects to blocked hosts.
- Task request validation trims input, rejects blank queries, and bounds competitor/dimension lists.
- Streamlit polling has a timeout, failed task display, report-not-ready handling, and escaped radar
  table content.
- PyMySQL is optional under the `mysql` extra; SQLite remains the default stable runtime.

## Validation Commands

```bash
python -m compileall app
python -m ruff check app/ tests/ frontend/streamlit_app.py
python -m mypy app/ --ignore-missing-imports
python -m pytest tests/ -v
```

Optional when Docker is available:

```bash
docker compose build
```

## Known Non-Blocking Deferred Items

See [deferred.md](deferred.md).

## No Feature Expansion

This stable pass intentionally avoids new agents, model providers, MCP write tools, auth, payment,
deployment platforms, queues, external databases, vector databases, and frontend framework changes.
