# Deferred Items

These items are non-blocking for the stable local release.

- MySQL remains an optional experiment only. The stable default uses SQLite; install the `mysql` extra
  only when deliberately testing a MySQL URL.
- Docker build validation depends on local Docker availability and should be run only in environments
  where Docker Desktop or an equivalent engine is already configured.
- Live search and live DeepSeek behavior depend on third-party availability. Local automated tests keep
  using fakes and stubs.
- Harness, MCP server, reranker, query rewrite, HyDE, and CRAG flags live in
  `.env.example.preview` and are not enabled by the stable runtime defaults.
- Optional UI dependency splitting is deferred because Docker and the simplest local install path still
  rely on `pip install .` including Streamlit.
- Full task snapshot persistence is deferred; v4.0.2 preserves stale task stage context without adding
  a schema migration.
- DNS resolution caching is demo-level optimization; full DNS rebinding IP pinning remains deferred.
