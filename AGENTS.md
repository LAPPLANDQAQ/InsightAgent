# InsightAgent Repository Instructions

InsightAgent v4 is a TODO-driven RAG Research Agent with Evidence Chain, Hybrid Retrieval, Harness Runtime, MCP Server, and evaluation metrics.

- Python: `>=3.12,<3.13`.
- Layering: `api -> services -> graph -> agents -> tools/rag/harness -> infra`.
- Agents orchestrate only. They must not directly call external SDKs, raw HTTP clients, databases, or filesystem side effects.
- Tests must not use real LLM APIs, real search APIs, real web pages, real LangFuse services, or real MCP clients.
- MCP must be safe by default: no shell execution, arbitrary SQL, arbitrary file writes, arbitrary HTTP fetch, or unsafe local file access.
- README metrics must separate target metrics from measured metrics. Do not claim measured values without committed evaluation output.
- One logical commit at a time when committing manually; avoid implementing unrelated future work in a single commit.

Suggested checks:

```bash
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m ruff check app tests
python -m mypy app --ignore-missing-imports
```
