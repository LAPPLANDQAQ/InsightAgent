"""Streamlit helper tests."""

import httpx

from frontend.components.task_form import is_active_task_running, should_disable_form
from frontend.utils import (
    MAX_CONSECUTIVE_POLL_FAILURES,
    ReportNotReadyError,
    _is_transient_http_error,
    _poll_timed_out,
    _radar_svg,
    _require_field,
    _stage_index,
    api_get_report_with_retries,
    get_api_base,
)


def test_api_base_defaults_to_backend_port(monkeypatch):
    monkeypatch.delenv("INSIGHT_API_BASE", raising=False)

    assert get_api_base() == "http://127.0.0.1:8000"


def test_api_base_env_override_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("INSIGHT_API_BASE", "http://api.test:9000/")

    assert get_api_base() == "http://api.test:9000"


def test_poll_timeout_helper():
    assert not _poll_timed_out(100.0, 109.0, 10)
    assert _poll_timed_out(100.0, 110.0, 10)


def test_transient_http_error_helper():
    request = httpx.Request("GET", "https://api.test/tasks/task")
    transient = httpx.HTTPStatusError(
        "service unavailable",
        request=request,
        response=httpx.Response(503, request=request),
    )
    rate_limited = httpx.HTTPStatusError(
        "rate limited",
        request=request,
        response=httpx.Response(429, request=request),
    )
    terminal = httpx.HTTPStatusError(
        "not found",
        request=request,
        response=httpx.Response(404, request=request),
    )

    assert _is_transient_http_error(transient)
    assert _is_transient_http_error(rate_limited)
    assert not _is_transient_http_error(terminal)


def test_require_field_raises_for_missing_backend_field():
    assert _require_field({"task_id": "task_1"}, "task_id") == "task_1"

    try:
        _require_field({}, "status")
    except ValueError as exc:
        assert "missing field: status" in str(exc)
    else:
        raise AssertionError("missing field did not raise")


def test_frontend_stage_list_is_english():
    assert _stage_index("planner") >= 0


def test_active_task_guard_disables_form_until_terminal_state():
    active = {"task_id": "task_1", "task_completed": False, "form_disabled": False}
    completed = {"task_id": "task_1", "task_completed": True, "form_disabled": False}
    submitting = {"task_id": None, "task_completed": False, "form_disabled": True}

    assert is_active_task_running(active)
    assert should_disable_form(active)
    assert not is_active_task_running(completed)
    assert not should_disable_form(completed)
    assert should_disable_form(submitting)


def test_submission_error_restores_form_disabled(monkeypatch):
    import frontend.streamlit_app as app

    class FakeState(dict):
        def __getattr__(self, name):
            return self[name]

        def __setattr__(self, name, value):
            self[name] = value

    class FakeStreamlit:
        def __init__(self) -> None:
            self.session_state = FakeState(form_disabled=False)
            self.errors: list[str] = []

        def error(self, message: str) -> None:
            self.errors.append(message)

    def fail_create_task(query: str, competitors: list[str], dimensions: list[str]) -> str:
        raise RuntimeError("offline")

    fake_st = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "api_create_task", fail_create_task)

    app._handle_submit({"query": "AI tools", "competitors": [], "dimensions": []})

    assert fake_st.session_state["form_disabled"] is False
    assert fake_st.errors


def test_polling_failure_limit_is_less_sensitive():
    assert MAX_CONSECUTIVE_POLL_FAILURES == 15


def test_report_fetch_retries_not_ready(monkeypatch):
    import frontend.utils as utils_module

    calls = 0

    def fake_get_report(task_id: str) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ReportNotReadyError("not ready")
        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "report_markdown": "# report",
            "quality_metrics": {},
        }

    monkeypatch.setattr(utils_module, "api_get_report", fake_get_report)
    monkeypatch.setattr(utils_module, "REPORT_RETRY_INTERVAL_SECONDS", 0)

    report = api_get_report_with_retries("task_1")

    assert report["report_markdown"] == "# report"
    assert calls == 2


def test_radar_svg_includes_escaped_table():
    svg = _radar_svg(
        [
            {"dimension": "<pricing>", "evidence_count": 2, "sufficient": True},
            {"dimension": "features", "evidence_count": 0, "sufficient": False},
        ]
    )

    assert "Dimension" in svg
    assert "Evidence Count" in svg
    assert "Sufficient" in svg
    assert "Needs Improvement" in svg
    assert "&lt;pricing&gt;" in svg
    assert "<pricing>" not in svg
