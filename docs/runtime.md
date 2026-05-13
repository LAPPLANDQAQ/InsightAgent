# Runtime

InsightAgent v4.0.2 is configured for a local stable demo path:

- DeepSeek-only runtime models: `deepseek-v4-pro`, `deepseek-v4-flash`, `deepseek-chat`, or `deepseek-reasoner`.
- SQLite default database and cache.
- Streamlit frontend with default API base `http://127.0.0.1:8000`.
- FastAPI task lifecycle with status polling, cancellation, stale-task failure context, and structured issue details.
- `/healthz` is process liveness. `/readyz` checks database, cache, config, and DeepSeek key readiness.

Experimental flags are listed in `.env.example.preview`; they are not enabled in the stable default runtime.
