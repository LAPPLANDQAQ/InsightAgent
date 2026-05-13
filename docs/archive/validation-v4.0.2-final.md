# Validation Record — InsightAgent v4.0.2 Final

> Final freeze-pass validation. This document is the evidence supporting
> `docs/release-v4.0.2-stable.md`.

## Run metadata

- Date: 2026-05-13 (local)
- Commit: `c4c4a6a235d5bf8eb6d97ab065856ec97b011594`
- Branch: `main`
- Working tree: clean before and after this run
- Python: 3.12.9
- Platform: Windows (`win32`), bash shell
- Validation harness: local CPython virtual environment with `pip install -e ".[dev]"` already applied prior to this run

## Validation commands and results

All commands run from repository root.

| # | Command | Result | Exit code | Notes |
|---|---------|--------|-----------|-------|
| 1 | `python -m compileall app frontend` | PASS | 0 | All `app/**` and `frontend/**` modules compiled. |
| 2 | `python -m ruff check app tests examples scripts frontend` | PASS | 0 | `All checks passed!` |
| 3 | `python -m mypy app --ignore-missing-imports` | PASS | 0 | `Success: no issues found in 123 source files`. |
| 4 | `python -m pytest tests -q` | PASS | 0 | `225 passed in 12.59s` |
| 5 | `docker compose build` | NOT RUN | n/a | Docker CLI not available in this environment (`docker: command not found`). |
| 6 | `docker compose up` | NOT RUN | n/a | Same reason as above. |
| 7 | Streamlit manual smoke (`streamlit run frontend/streamlit_app.py`) | NOT RUN | n/a | Requires an interactive browser session, deliberately deferred. |

### Captured stdout snippets

```text
compileall:
  Listing 'app'... ... Compiling 'frontend/utils.py'...
  Exit code: 0

ruff:
  All checks passed!

mypy:
  Success: no issues found in 123 source files

pytest:
  ........................................................................ [ 32%]
  ........................................................................ [ 64%]
  ........................................................................ [ 96%]
  .........                                                                [100%]
  225 passed in 12.59s
```

## Hard-stop checklist (per freeze prompt §4)

| Hard-stop item | State | Evidence |
|----------------|-------|----------|
| Frontend default API base is `127.0.0.1:8000` | OK | `frontend/utils.py:16` returns `http://127.0.0.1:8000` when `INSIGHT_API_BASE` unset. |
| `pyproject` version is `4.0.2` | OK | `pyproject.toml:3` `version = "4.0.2"`. |
| `POST /api/tasks` returns `201` | OK | `app/api/tasks.py:29` `status_code=status.HTTP_201_CREATED`. |
| `DELETE /api/tasks` status payload aligned | OK | Returns `{"status": "FAILED", "detail": "task cancellation accepted"}` with HTTP 202, matching persisted state. |
| `/healthz` and `/readyz` split | OK | Two distinct routes in `app/api/health.py`, `/readyz` sets 503 when probe fails. |
| `ExtractionTool` truncates `>2000` chars instead of rejecting | OK | `app/tools/extraction_tool.py:189` `normalized[:MAX_EXTRACTION_CHARS]`. |
| `SufficiencyTool` decides `is_sufficient` by threshold only | OK | `app/tools/sufficiency_tool.py:63` `is_sufficient=score >= threshold`. No `not missing` requirement. |
| Writer fallback emits bracketed evidence refs | OK | `app/agents/writer.py:80` wraps each ref as `[ev_*]`. |
| Critic skips metadata bullets | OK | `app/agents/critic.py:20` METADATA_BULLET_PREFIXES covers Chinese half/full-width and English Scope/Sources/Evidence. |
| `form_disabled` / active-task guard active | OK | `frontend/components/task_form.py:17-21` `should_disable_form()` consumed by submit + new-task buttons. |
| DeepSeek-only provider guard intact | OK | `app/config.py:104-116` `validate_runtime_models` enforces DeepSeek whitelist when guard enabled. |
| LLM retry/fallback | OK | `app/infra/llm/deepseek_client.py:138-177` retries transient errors then promotes to `fallback` role. |
| LLM semaphores present | OK | `deepseek_client.py:48-49` heavy + light semaphores; sized from settings. |
| Fetch client reuse + aclose | OK | `HttpxFetchClient.__init__` reuses one `AsyncClient`; `aclose()` closes it; `Container.aclose` awaits it. |
| FastAPI shutdown closes container/fetch/LLM/engine | OK | `app/main.py:18-35` lifespan awaits `task_service.shutdown`, `container.aclose`, `engine.dispose`. |
| pytest / ruff / mypy / compileall pass | OK | See table above. |

No hard-stop item is broken. No code change was needed for this freeze pass.

## Files changed in this run

- `docs/archive/validation-v4.0.2-final.md` (this file)
- `docs/release-v4.0.2-stable.md` (final release note)

No source files in `app/`, `frontend/`, or `tests/` were modified.

## Honesty boundaries

This validation deliberately does **not** claim:

- Docker image build verified — Docker CLI not installed in this environment.
- `docker compose up` runtime smoke verified — same reason.
- Live DeepSeek API smoke — out of scope, deferred.
- Live Tavily API smoke — out of scope, deferred.
- Measured RAG hit-rate / citation validity / coverage numbers — design targets remain `TBD` in README.

The test suite uses fake/stub/mock clients only.

## Deferred items (no action this run)

Tracked in `docs/deferred.md`. None are release-blocking for v4.0.2-stable.
