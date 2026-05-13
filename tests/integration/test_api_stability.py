"""API stability integration tests."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.infra.db.session import build_engine, build_session_factory
from app.services.task_service import TaskService


class FakeGraph:
    """Fake graph for API task lifecycle tests."""

    def __init__(self, result: dict | None = None, error: Exception | None = None) -> None:
        self.result = result or {
            "task_status": "COMPLETED",
            "current_stage": "finalize",
            "draft_report": "# draft",
            "final_report": "# final",
            "issues": [],
            "competitors": [],
            "sufficiency": {"score": 1.0},
        }
        self.error = error

    async def ainvoke(self, state: dict) -> dict:
        """Return a result or raise the configured error."""
        if self.error:
            raise self.error
        return {**state, **self.result}


def _create_test_app(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    monkeypatch.setenv("DB_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    get_settings.cache_clear()
    return app


def _install_task_service(app, container_with_stubs, graph: FakeGraph, tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'tasks.db'}")
    session_factory = build_session_factory(engine)
    service = TaskService(container_with_stubs, session_factory, run_background=False)
    service.graph = graph
    app.state.task_service = service


def test_healthz_reports_liveness(monkeypatch, tmp_path):
    app = _create_test_app(monkeypatch, tmp_path)

    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_reports_runtime_readiness(monkeypatch, tmp_path):
    app = _create_test_app(monkeypatch, tmp_path)

    response = TestClient(app).get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db"] == "ok"
    assert payload["cache"] == "ok"
    assert payload["llm_provider"] == "deepseek"
    assert payload["llm_configured"] is True


def test_readyz_degraded_when_db_check_fails(monkeypatch, tmp_path):
    class BrokenEngine:
        def connect(self):
            raise RuntimeError("db failed with test-key")

    app = _create_test_app(monkeypatch, tmp_path)
    app.state.engine = BrokenEngine()

    response = TestClient(app).get("/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["db"] == "error: RuntimeError"
    assert "test-key" not in response.text


def test_api_create_status_and_report_with_stub_task(monkeypatch, tmp_path, container_with_stubs):
    app = _create_test_app(monkeypatch, tmp_path)
    _install_task_service(app, container_with_stubs, FakeGraph(), tmp_path)
    client = TestClient(app)

    created = client.post("/api/tasks", json={"query": "AI coding assistants"})
    task_id = created.json()["task_id"]
    status = client.get(f"/api/tasks/{task_id}")
    report = client.get(f"/api/tasks/{task_id}/report")

    assert created.status_code == 200
    assert status.json()["status"] == "COMPLETED"
    assert report.json()["report_markdown"] == "# final"


def test_api_failed_task_status_exposes_issue(monkeypatch, tmp_path, container_with_stubs):
    app = _create_test_app(monkeypatch, tmp_path)
    graph = FakeGraph(error=RuntimeError("upstream timeout"))
    _install_task_service(app, container_with_stubs, graph, tmp_path)
    client = TestClient(app)

    created = client.post("/api/tasks", json={"query": "AI coding assistants"})
    task_id = created.json()["task_id"]
    status = client.get(f"/api/tasks/{task_id}")
    report = client.get(f"/api/tasks/{task_id}/report")

    assert status.status_code == 200
    assert status.json()["status"] == "FAILED"
    assert status.json()["issues"] == ["upstream timeout"]
    assert report.status_code == 404


def test_api_task_status_keeps_legacy_and_structured_issues(
    monkeypatch,
    tmp_path,
    container_with_stubs,
):
    app = _create_test_app(monkeypatch, tmp_path)
    _install_task_service(app, container_with_stubs, FakeGraph(), tmp_path)
    app.state.task_service.get_status = lambda task_id: {
        "status": "FAILED",
        "stage": "failed",
        "stage_label": "Failed",
        "progress": 1.0,
        "estimated_remaining_seconds": 0,
        "issues": ["task cancelled by user"],
        "structured_issues": [
            {
                "type": "cancellation",
                "severity": "warning",
                "stage": "failed",
                "message": "task cancelled by user",
            }
        ],
    }
    client = TestClient(app)

    response = client.get("/api/tasks/task_cancelled")

    assert response.status_code == 200
    payload = response.json()
    assert payload["issues"] == ["task cancelled by user"]
    assert payload["structured_issues"][0]["type"] == "cancellation"


def test_api_cancel_running_task_returns_202(monkeypatch, tmp_path, container_with_stubs):
    app = _create_test_app(monkeypatch, tmp_path)

    async def cancel(task_id: str) -> bool:
        return task_id == "task_running"

    app.state.task_service = SimpleNamespace(cancel=cancel)
    client = TestClient(app)

    response = client.delete("/api/tasks/task_running")

    assert response.status_code == 202
    assert response.json() == {"task_id": "task_running", "status": "CANCELLING"}


def test_api_cancel_unknown_task_returns_404(monkeypatch, tmp_path, container_with_stubs):
    app = _create_test_app(monkeypatch, tmp_path)

    async def cancel(task_id: str) -> bool:
        return False

    app.state.task_service = SimpleNamespace(cancel=cancel)
    client = TestClient(app)

    response = client.delete("/api/tasks/missing")

    assert response.status_code == 404


def test_api_queue_full_response_includes_retry_after(
    monkeypatch,
    tmp_path,
    container_with_stubs,
):
    app = _create_test_app(monkeypatch, tmp_path)
    _install_task_service(app, container_with_stubs, FakeGraph(), tmp_path)
    app.state.task_service.repository.active_task_count = lambda: 999
    client = TestClient(app)

    response = client.post("/api/tasks", json={"query": "AI coding assistants"})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
