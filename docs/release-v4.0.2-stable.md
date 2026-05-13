# InsightAgent v4.0.2 — Stable Release Note

## Release scope

This release closes out the v4.0 line as a stable, freezeable local research
agent. It is **not** a feature release — every change since v4.0.1 is either a
stability fix, a documentation correction, or a small frontend refresh. No new
agents, providers, infrastructure dependencies, or experimental subsystems
were enabled.

Runtime constraints, preserved by this release:

- Runtime LLM provider: **DeepSeek only** (`deepseek-v4-pro`,
  `deepseek-v4-flash`, `deepseek-chat`, `deepseek-reasoner`).
- Frontend: **Streamlit only**, default bind `127.0.0.1:8501`, defaults to
  `http://127.0.0.1:8000` for the backend.
- Storage: **SQLite** for both data and cache (memory cache available for
  tests).
- Default workflow: `Planner → Researcher → Analyst → Writer → Critic`.
- RAG / Harness / MCP: present in the tree but **disabled by default**.

## Main features carried forward

- FastAPI backend with `/healthz` + `/readyz` split and lifespan-managed
  resource cleanup.
- LangGraph-driven workflow with critic-guided routing and bounded iteration
  count.
- DeepSeek client with retry, fallback model, and heavy/light concurrency
  semaphores.
- Researcher with controlled per-source extraction, classifier-tagged
  sources, fallback evidence when extraction fails.
- Critic that rejects empty reports, missing dimensions, invalid evidence
  refs, and unsupported claim bullets — while ignoring well-known metadata
  bullets in both English and Chinese.
- Streamlit dual-language UI (中文 / English), task history, status polling
  with backoff, evidence viewer, coverage radar fallback.
- SSRF-protected HTTP fetch client with shared async session and explicit
  shutdown.
- Task service with timeout, cancellation, semaphore-limited concurrency,
  and persisted task state in SQLite.

## Stability fixes since v4.0.1

The following are the load-bearing fixes that justify the v4.0.2 tag. They
were all merged before this freeze pass; this release simply ratifies them.

- FastAPI shutdown now disposes the SQLAlchemy engine in addition to closing
  the container, fetch client, and DeepSeek client.
- `DeepSeekClient.aclose()` ensures the underlying OpenAI-compatible HTTP
  client is closed.
- `Container.aclose()` closes LLM and fetch resources together.
- `POST /api/tasks` returns `201 Created` (was `200`).
- `DELETE /api/tasks/{id}` response status now matches the persisted
  failed/cancelled state.
- `ExtractionTool` truncates source text at 2000 chars instead of refusing
  long inputs.
- `SufficiencyTool.is_sufficient` is derived from the coverage score
  crossing the threshold — `missing_dimensions` is informational only.
- `Writer._fallback_report` emits each evidence reference as `[ev_*]`, so
  `Critic` can distinguish supported bullets from unsupported claims.
- `Critic` skips metadata bullets with English **and** Chinese half/full
  width prefixes (`- 竞品:`, `- 竞品：`, `- 维度:` / `维度：`,
  `- 证据:` / `证据：`, plus `- Competitors:` / `- Dimensions:` /
  `- Evidence:` / `- Scope:` / `- Sources:`).
- Frontend default API base is `127.0.0.1:8000`, version label shows
  `v4.0.2`, lingering English placeholder translations replaced with real
  Chinese.
- Frontend submit button + new-task button are gated by
  `should_disable_form()` to prevent duplicate submissions while a task is
  active.
- `.env.example` slimmed to runtime essentials; experimental flags moved to
  `.env.example.preview`.

## Validation evidence

All validation was performed from this commit
(`c4c4a6a235d5bf8eb6d97ab065856ec97b011594`) on 2026-05-13.

| Check | Result | Notes |
|-------|--------|-------|
| `python -m compileall app frontend` | PASS | Exit 0. |
| `python -m ruff check app tests examples scripts frontend` | PASS | `All checks passed!` |
| `python -m mypy app --ignore-missing-imports` | PASS | `Success: no issues found in 123 source files`. |
| `python -m pytest tests -q` | PASS | `225 passed in 12.59s`. |
| `docker compose build` | NOT VERIFIED | Docker CLI not available in this environment. |
| `docker compose up` | NOT VERIFIED | Same as above. |
| Streamlit manual smoke | NOT VERIFIED | Requires an interactive browser session, deliberately deferred. |

Full evidence trail: `docs/archive/validation-v4.0.2-final.md`.

The test suite uses fake/stub/mock clients only; no real DeepSeek, Tavily,
network, or browser dependency is required to reproduce these results.

## Known non-blocking deferred items

These items remain in `docs/deferred.md` and are explicitly out of scope for
v4.0.2:

- Optional UI dependency split.
- Full `snapshot_json` for tasks.
- DNS-rebinding custom transport (current SSRF guard remains the supported
  protection layer).
- Real DeepSeek nightly smoke test.
- Real Tavily smoke test.
- Frontend localStorage task history.
- Authentication / user accounts.
- Production queue, Redis, Celery, vector DB, or other infra rewrites.
- API versioning.
- Large MCP / Harness redesign.
- RAG sufficiency-loop expansion.

None of these block the freeze. They are tracked for future scoped work.

## Honesty boundaries

This release note does **not** claim:

- Docker image is verified — it is not, in this environment.
- Production-ready deployment — explicitly out of scope.
- Real DeepSeek or Tavily smoke tested — they are not, in this environment.
- Measured RAG metrics — target values in `README.md` remain `TBD` until a
  trustworthy evaluation pass is run separately.

## Final recommendation

`v4.0.2-stable` is **ready to freeze**. No release-blocking issue was found
during this freeze audit; all required local validation commands passed
without modifications to source code. Docker and live-API smoke remain
deferred and are honestly reported as such.

After this release, the project should stop accepting non-critical changes
until a new release line is opened.
