# Deferred Items

These items are non-blocking for the stable local release.

- MySQL remains an optional experiment only. The stable default uses SQLite; install the `mysql` extra
  only when deliberately testing a MySQL URL.
- Docker build validation depends on local Docker availability and should be run only in environments
  where Docker Desktop or an equivalent engine is already configured.
- Live search and live DeepSeek behavior depend on third-party availability. Local automated tests keep
  using fakes and stubs.
