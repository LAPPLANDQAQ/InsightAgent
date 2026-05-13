# InsightAgent v4.0.2

InsightAgent is a local TODO-driven research agent for competitive analysis. The stable runtime uses FastAPI, LangGraph, Streamlit, SQLite, and DeepSeek through an OpenAI-compatible transport.

## Stable Scope

- Runtime LLM provider: DeepSeek only.
- Default database and cache: SQLite under `./data`.
- Frontend: Streamlit dashboard.
- Default workflow: `Planner -> Researcher -> Analyst -> Writer -> Critic`.
- Optional RAG path stays disabled unless `ENABLE_RAG_RESEARCH=true`.
- Harness and MCP settings are archived/experimental and disabled in the stable runtime.

The codebase keeps this layering boundary:

```text
api -> services -> graph -> agents -> tools/rag/harness -> infra
```

Agents orchestrate only. External SDKs, HTTP clients, database access, and filesystem side effects stay in tools/services/infra.

## Install

Use Python 3.12.

```bash
python -m venv .venv
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `DEEPSEEK_API_KEY` for live runs. Tests use fakes and do not need live API keys.

## Run Locally

Start the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check liveness and readiness:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

Start Streamlit:

```bash
streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=127.0.0.1
```

The Streamlit frontend defaults to `INSIGHT_API_BASE=http://127.0.0.1:8000`. Override it only when the API runs elsewhere.

## API

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"AI coding assistant market\",\"competitors\":[\"Cursor\",\"GitHub Copilot\"],\"dimensions\":[\"pricing\",\"features\",\"ecosystem\"]}"
```

Check task status:

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}
```

Cancel a running task:

```bash
curl -X DELETE http://127.0.0.1:8000/api/tasks/{task_id}
```

Fetch the report:

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}/report
```

## Validation

Recommended local checks:

```bash
python -m compileall app frontend
python -m ruff check app tests examples scripts frontend
python -m mypy app --ignore-missing-imports
python -m pytest tests -q
```

Optional, when Docker is available:

```bash
docker compose build
```

## Metrics

The values below are target metrics, not measured claims. Keep measured values as `TBD` unless committed evaluation output exists.

| Metric | Target | Measured |
|---|---:|---:|
| RAG Hit@5 | >= 0.90 | TBD |
| MRR | >= 0.85 | TBD |
| Citation validity | >= 95% | TBD |
| Dimension coverage | >= 90% | TBD |
| TODO completion | >= 95% | TBD |

## Docs

- [Docs Index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Runtime](docs/runtime.md)
- [RAG](docs/rag.md)
- [Deferred Items](docs/deferred.md)
