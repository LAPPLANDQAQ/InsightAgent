# InsightAgent v4 Second-Round Acceptance Report

Date: 2026-05-11
Validator: Codex
Environment: Windows / PowerShell, Python 3.12.9
Repository: https://github.com/LAPPLANDQAQ/InsightAgent
Branch: main
Commit: 03e16dcd292d49b6a1f297c781d50dc29f4e8670
Python: Python 3.12.9

## 1. Overall Status

Overall Status: CONDITIONALLY PASS

All required local code-level checks passed. Docker Compose was skipped because Docker is not installed in this environment. GitHub Actions latest `main` run was verified locally as completed successfully.

## 2. Summary Table

| Check | Status | Notes |
|---|---|---|
| Repository clean | PASS | Clean before report generation; final status contains only this generated report. |
| Python 3.12 | PASS | `Python 3.12.9`. |
| Editable install | PASS | `pip install -e ".[dev]"` passed under elevated filesystem permission; prior setuptools blocker is fixed. |
| Config smoke | PASS | Dummy env loaded all v4 feature flags. |
| Ruff | PASS | `All checks passed!` |
| Mypy | PASS | `Success: no issues found in 116 source files`. |
| Full pytest | PASS | `120 passed, 1 warning`. |
| Unit tests | PASS | `81 passed, 1 warning`. |
| Integration tests | PASS | `3 passed, 1 warning`. |
| Feature flag legacy workflow | PASS | `ENABLE_RAG_RESEARCH=false`: `3 passed, 1 warning`. |
| Feature flag RAG workflow | PASS | `ENABLE_RAG_RESEARCH=true -k "rag or feature or workflow"`: `3 passed, 1 warning`. |
| Evaluation tests | PASS | `6 passed, 1 warning`. |
| Harness tests | PASS | `10 passed, 1 warning`. |
| MCP tests | PASS | `5 passed, 1 warning`. |
| Architecture tests | PASS | `14 passed, 1 warning`. |
| E2E tests | PASS | `1 passed, 1 warning`. |
| RAG demo | PASS | Printed Markdown report with `[ev_todo_cursor_pricing_1]`. |
| MCP demo | PASS | Returned `{"ok":true,...}`. |
| Harness demo | PASS | Replay snapshot redacted `api_key` as `[REDACTED]`. |
| RAG component smoke | PASS | Cleaned text, created 2 chunks, retrieved 1 chunk. |
| FastAPI smoke | PASS | Import passed; port 8000 was occupied, rerun on 8010 returned 200 for `/openapi.json` and `/docs`. |
| Streamlit smoke | PASS | Compile passed; headless process stayed alive. |
| Docker Compose | SKIPPED | Docker CLI is not installed. |
| GitHub Actions config | PASS | CI installs editable package and runs ruff, mypy, pytest, and demos. |
| GitHub Actions run status | PASS | `gh run list` showed latest `main` CI run completed with success. |

## 3. Previously Failed Items

### 3.1 Packaging install

- Previous status: Failed because setuptools discovered multiple top-level packages.
- Current status: PASS.
- Evidence: `pyproject.toml` has `[tool.setuptools.packages.find]`, `where = ["."]`, `include = ["app*"]`, and excludes data/logs/frontend/run_logs/scripts/tests/docs/examples. `pip install -e ".[dev]"` built and installed `insight-agent-0.1.0`.
- Verdict: Fixed.

### 3.2 Feature-flag workflow isolation

- Previous status: Failed when `ENABLE_RAG_RESEARCH=true` polluted legacy workflow integration fixtures and caused missing RAG agent attributes.
- Current status: PASS.
- Evidence: Integration tests passed with `ENABLE_RAG_RESEARCH=false`, and the RAG/feature/workflow subset passed with `ENABLE_RAG_RESEARCH=true`.
- Verdict: Fixed.

## 4. Command Log

| Command | Exit code | Result | Important output |
|---|---:|---|---|
| `git status --short` | 0 | PASS | No output; clean worktree. |
| `git branch --show-current` | 0 | PASS | `main`. |
| `git log --oneline -n 20` | 0 | PASS | Head: `03e16dc docs: record first acceptance fixes`. |
| `python --version` | 0 | PASS | `Python 3.12.9`. |
| `git fetch origin` | 1 | RETRIED | Sandbox permission error: `cannot open '.git/FETCH_HEAD': Permission denied`. |
| `git fetch origin` elevated | 0 | PASS | Fetch succeeded. |
| `git checkout main` | 1 | RETRIED | Sandbox permission error: `Unable to create ... .git/index.lock: Permission denied`. |
| `git checkout main` elevated | 0 | PASS | `Already on 'main'`; branch up to date. |
| `git pull origin main` | 1 | RETRIED | Sandbox permission error: `cannot open '.git/FETCH_HEAD': Permission denied`. |
| `git pull origin main` elevated | 0 | PASS | `Already up to date.` |
| `git rev-parse HEAD` | 0 | PASS | `03e16dcd292d49b6a1f297c781d50dc29f4e8670`. |
| `rg -n "tool\.setuptools\|packages\.find\|include =\|exclude =\|where =" pyproject.toml` | 0 | PASS | Setuptools package discovery block found. |
| `Get-Content pyproject.toml` | 0 | PASS | Includes only `app*`; excludes non-package top-level folders. |
| `python -m pip install --upgrade pip` | 0 | PASS | Pip already satisfied at `26.1.1`. |
| `pip install -e ".[dev]"` | 1 | RETRIED | Built editable wheel, then hit sandbox/user-site write error `[WinError 5] Access denied: C:\Users\wth\AppData\Roaming\Python`. |
| `pip install -e ".[dev]"` elevated | 0 | PASS | Successfully built and installed `insight-agent-0.1.0`. |
| Dummy-env config smoke | 0 | PASS | Printed `enable_rag_research: False`, `enable_harness: True`, `enable_mcp_server: True`, and `config smoke ok`. |
| `python -m ruff check app tests examples scripts frontend` | 0 | PASS | `All checks passed!` |
| `python -m mypy app --ignore-missing-imports` | 0 | PASS | `Success: no issues found in 116 source files`. |
| `python -m pytest -q` | 0 | PASS | `120 passed, 1 warning in 2.76s`. |
| `python -m pytest tests/unit -q` | 0 | PASS | `81 passed, 1 warning`. |
| `python -m pytest tests/integration -q` | 0 | PASS | `3 passed, 1 warning`. |
| `python -m pytest tests/evaluation -q` | 0 | PASS | `6 passed, 1 warning`. |
| `python -m pytest tests/harness -q` | 0 | PASS | `10 passed, 1 warning`. |
| `python -m pytest tests/mcp -q` | 0 | PASS | `5 passed, 1 warning`. |
| `python -m pytest tests/architecture -q` | 0 | PASS | `14 passed, 1 warning`. |
| `python -m pytest tests/e2e -q` | 0 | PASS | `1 passed, 1 warning`. |
| `python examples/rag_research_demo.py` | 0 | PASS | Printed `# Demo Report` and `[ev_todo_cursor_pricing_1]`. |
| `python examples/mcp_stdio_demo.py` | 0 | PASS | `{"ok":true,"result":{"final_report":"# Demo"},"error":null}`. |
| `python examples/harness_replay_demo.py` | 0 | PASS | Replay snapshot contains `api_key: [REDACTED]`. |
| Inline RAG component smoke | 0 | PASS | `chunks: 2`, `retrieved: 1`, `rag component smoke ok`. |
| `ENABLE_RAG_RESEARCH=false; python -m pytest tests/integration -q` | 0 | PASS | `3 passed, 1 warning`. |
| `ENABLE_RAG_RESEARCH=true; python -m pytest tests/integration -q -k "rag or feature or workflow"` | 0 | PASS | `3 passed, 1 warning`. |
| `python -c "import app.mcp_server.server, app.mcp_server.tools, app.mcp_server.security; print('mcp imports ok')"` | 0 | PASS | `mcp imports ok`. |
| `'{...get_report...}' \| python -m app.mcp_server.server --transport stdio` | 0 | PASS | `{"ok":true,"result":{"final_report":""},"error":null}`. |
| `python -c "from app.main import app; print('fastapi app import ok')"` | 0 | PASS | `fastapi app import ok`. |
| Uvicorn smoke on port 8000 | 1 | RETRIED | Port occupied: `[Errno 10048] ... bind on address ('127.0.0.1', 8000)`. |
| Uvicorn smoke on port 8010 | 0 | PASS | `openapi: 200`, `docs: 200`. |
| `python -m py_compile frontend\streamlit_app.py` | 0 | PASS | No output. |
| Streamlit headless smoke on port 8502 | 0 | PASS | `streamlit smoke ok`. |
| `docker --version` | 1 | SKIPPED | Docker command not found. Compose not run. |
| Docs and CI `rg` inspection | 0 | PASS | README/docs/env/CI references found for v4, demos, flags, TBD metrics, and CI commands. |
| `Get-Content .github\workflows\ci.yml` | 0 | PASS | CI uses Python 3.12, `pip install -e ".[dev]"`, ruff, mypy, pytest, demo smoke. |
| `rg` RAG smoke docs inspection | 0 | PASS | `docs/rag_engine.md` uses current `TextCleaner`, `ParentChildChunker`, and `SparseRetriever` API. |
| `rg` MCP safety inspection | 0 | PASS | Docs/tests confirm read-only MCP and rejection of unsafe tools/URLs. |
| `gh --version` | 0 | PASS | `gh version 2.89.0`. |
| `gh run list --branch main --limit 5` | 0 | PASS | Latest CI on `main`: `completed success`, run `25663660357`. |
| `Get-Content app\mcp_server\tools.py` | 0 | PASS | Exposes only `list_tasks`, `get_report`, `retrieve_research_chunks`, `get_evidences`. |
| `Get-Content app\mcp_server\security.py` | 0 | PASS | Rejects non-http schemes, localhost/private/link-local access by default, and redacts secret-looking values. |
| Pre-report `git status --short` | 0 | PASS | No output; clean before adding this report. |
| Final `git status --short` | 0 | PASS | `?? InsightAgent_v4_second_acceptance_report_2026-05-11.md` only. |

## 5. Failures

No project-level required check failed.

Environment-level failed attempts were handled as follows:

Failure: sandbox blocked Git metadata writes
Command: `git fetch origin`, `git checkout main`, `git pull origin main`
Exit code: 1 before elevation
Key error: permission denied opening `.git/FETCH_HEAD` or creating `.git/index.lock`
Suspected root cause: sandbox restriction on `.git` writes
Minimal fix suggestion: run these repository-sync commands with approved filesystem permission when validation requires syncing
Files likely involved: `.git/FETCH_HEAD`, `.git/index.lock`
Severity: LOW

Failure: sandbox/user-site permission blocked first editable install attempt
Command: `pip install -e ".[dev]"`
Exit code: 1 before elevation
Key error: `[WinError 5] Access denied: C:\Users\wth\AppData\Roaming\Python`
Suspected root cause: sandbox restriction on Python user site-packages
Minimal fix suggestion: run install with approved filesystem permission or use a writable virtual environment
Files likely involved: Python user site-packages
Severity: LOW

Failure: FastAPI smoke port 8000 occupied
Command: Uvicorn smoke on port 8000
Exit code: 1
Key error: `[Errno 10048] ... only one usage of each socket address is normally permitted`
Suspected root cause: another local process already bound to port 8000
Minimal fix suggestion: use an alternate smoke port; rerun on 8010 passed
Files likely involved: none
Severity: LOW

## 6. Warnings

- Docker is not installed, so Docker Compose was skipped.
- Pytest emitted cache warnings because it could not write `.pytest_cache` under the current sandbox permissions. Tests passed despite the warnings.
- The first non-elevated editable install attempt built successfully but could not write to the Python user site. The elevated retry passed.

## 7. Security and Compliance Check

- No real API keys were provided or printed.
- No real LLM, search, LangFuse, or MCP client service calls were intentionally made.
- Tests and demos used local deterministic data.
- Harness demo redacted secret-like values.
- MCP remains read-only and safe by default.
- MCP exposed tools are only `list_tasks`, `get_report`, `retrieve_research_chunks`, and `get_evidences`.
- No shell execution, arbitrary SQL, arbitrary file write, or unsafe local file access MCP tool is exposed.
- README metrics keep measured values as `TBD`; target metrics are separate from measured metrics.

## 8. Final Verdict

CONDITIONALLY PASS:

All required local code-level checks passed, including editable install, ruff, mypy, full pytest, layered pytest, demos, RAG component smoke, feature-flag workflow checks, FastAPI, Streamlit, MCP, harness, and evaluation validation. Docker Compose was skipped because Docker is not installed. GitHub Actions latest `main` CI run was verified as successful.

## 9. Next Actions

1. Install Docker and run `docker compose up --build` if Docker Compose acceptance is required.
2. Resolve local `.pytest_cache` write permissions or run validation from a writable virtual workspace to remove pytest cache warnings.
3. Keep README measured metrics as `TBD` until committed evaluation output exists.
