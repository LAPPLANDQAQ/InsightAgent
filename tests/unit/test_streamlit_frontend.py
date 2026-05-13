"""Streamlit helper tests."""

import httpx

from frontend.utils import (
    ReportNotReadyError,
    _is_transient_http_error,
    _poll_timed_out,
    _radar_svg,
    _require_field,
    _stage_index,
    api_get_report_with_retries,
)


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
