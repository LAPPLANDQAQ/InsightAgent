"""Streamlit frontend for InsightAgent."""

import html
import math
import os
import time
from typing import Any

import httpx
import streamlit as st
import streamlit.components.v1 as components

from frontend.components.evidence_viewer import citation_summary

API_BASE = os.getenv("INSIGHT_API_BASE", "http://127.0.0.1:8000").rstrip("/")
POLL_INTERVAL_SECONDS = 2
MAX_POLL_SECONDS = int(os.getenv("INSIGHT_FRONTEND_MAX_POLL_SECONDS", "900"))
REPORT_RETRY_ATTEMPTS = 3
REPORT_RETRY_INTERVAL_SECONDS = 1
TRANSIENT_STATUS_CODES = {429, 503}
HTTP_CLIENT = httpx.Client(
    timeout=20.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)
FINAL_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}
STAGES = [
    ("queued", "Queued"),
    ("planner", "Planning"),
    ("researcher", "Researching"),
    ("sufficiency_check", "Checking Evidence Sufficiency"),
    ("analyst", "Analyzing"),
    ("writer", "Writing Report"),
    ("critic", "Reviewing"),
    ("finalize", "Finalizing"),
]


class ReportNotReadyError(RuntimeError):
    """Raised when the API reports that a task has no report yet."""


def _format_eta(seconds: int | None) -> str:
    """Format estimated remaining time."""
    if seconds is None:
        return "Estimating"
    if seconds <= 0:
        return "Done"
    minutes, remainder = divmod(seconds, 60)
    if minutes:
        return f"About {minutes}m {remainder}s"
    return f"About {remainder}s"


def _stage_index(stage: str | None) -> int:
    """Return the current stage index."""
    for index, (name, _) in enumerate(STAGES):
        if name == stage:
            return index
    return -1


def _is_transient_http_error(exc: httpx.HTTPStatusError) -> bool:
    """Return whether an HTTP status error should be retried while polling."""
    return exc.response.status_code in TRANSIENT_STATUS_CODES


def _require_field(payload: dict[str, Any], field: str) -> Any:
    """Return a required backend response field."""
    if field not in payload:
        raise ValueError(f"Backend response missing field: {field}")
    return payload[field]


def _render_status_panel(status: dict[str, Any] | None) -> None:
    """Render the right-side status visualization."""
    st.subheader("Run Status")
    if status is None:
        st.info("Waiting for a task")
        st.progress(0.0)
        for _, label in STAGES:
            st.caption(f"- {label}")
        return

    progress = float(status.get("progress") or 0.0)
    current_stage = status.get("current_stage")
    current_index = _stage_index(current_stage)
    st.metric("Status", status.get("status", "UNKNOWN"))
    st.metric("Stage", status.get("stage_label") or current_stage or "Unknown")
    st.metric("ETA", _format_eta(status.get("estimated_remaining_seconds")))
    st.progress(progress, text=f"{progress:.0%}")

    st.markdown("#### Stages")
    for index, (stage, label) in enumerate(STAGES):
        if index < current_index or status.get("status") in FINAL_STATUSES:
            marker = "[x]"
        elif index == current_index:
            marker = "[>]"
        else:
            marker = "[ ]"
        st.caption(f"{marker} {label} `{stage}`")

    issues = [str(issue) for issue in status.get("issues") or [] if str(issue).strip()]
    if issues:
        st.markdown("#### Issues")
        for issue in issues[:8]:
            st.warning(issue)


def _create_task(query: str, competitors: list[str], dimensions: list[str]) -> str:
    """Create a task through the API."""
    response = HTTP_CLIENT.post(
        f"{API_BASE}/api/tasks",
        json={"query": query, "competitors": competitors, "dimensions": dimensions},
    )
    response.raise_for_status()
    payload = response.json()
    return str(_require_field(payload, "task_id"))


def _get_status(task_id: str) -> dict[str, Any]:
    """Fetch task status."""
    response = HTTP_CLIENT.get(f"{API_BASE}/api/tasks/{task_id}")
    response.raise_for_status()
    payload = response.json()
    _require_field(payload, "status")
    return payload


def _get_report(task_id: str) -> dict[str, Any]:
    """Fetch task report."""
    response = HTTP_CLIENT.get(f"{API_BASE}/api/tasks/{task_id}/report")
    if response.status_code == 404:
        raise ReportNotReadyError("Report is not ready yet. Please refresh later.")
    response.raise_for_status()
    payload = response.json()
    _require_field(payload, "task_id")
    _require_field(payload, "status")
    _require_field(payload, "report_markdown")
    _require_field(payload, "quality_metrics")
    return payload


def _get_report_with_retries(task_id: str) -> dict[str, Any]:
    """Fetch a report with a short grace period after a final status."""
    last_error: ReportNotReadyError | None = None
    for attempt in range(REPORT_RETRY_ATTEMPTS):
        try:
            return _get_report(task_id)
        except ReportNotReadyError as exc:
            last_error = exc
            if attempt < REPORT_RETRY_ATTEMPTS - 1:
                time.sleep(REPORT_RETRY_INTERVAL_SECONDS)
    raise last_error or ReportNotReadyError("Report is not ready yet. Please refresh later.")


def _split_csv(text: str) -> list[str]:
    """Split comma separated input into normalized values."""
    return [item.strip() for item in text.replace("\uff0c", ",").split(",") if item.strip()]


def _coverage_items(quality_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized radar coverage items from quality metrics."""
    raw_items = quality_metrics.get("coverage") or []
    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "").strip()
        if not dimension:
            continue
        items.append(
            {
                "dimension": dimension,
                "evidence_count": int(item.get("evidence_count") or 0),
                "sufficient": bool(item.get("sufficient")),
            }
        )
    return items


def _radar_svg(items: list[dict[str, Any]]) -> str:
    """Build an SVG radar chart for dimension coverage."""
    width = 620
    height = 460
    center_x = width / 2
    center_y = 225
    radius = 145
    max_count = max([int(item["evidence_count"]) for item in items] + [1])
    count = len(items)

    def point(index: int, scale: float) -> tuple[float, float]:
        angle = -math.pi / 2 + (2 * math.pi * index / count)
        x = center_x + math.cos(angle) * radius * scale
        y = center_y + math.sin(angle) * radius * scale
        return x, y

    grid = []
    for scale in (0.25, 0.5, 0.75, 1.0):
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, scale) for i in range(count)))
        grid.append(f'<polygon points="{points}" fill="none" stroke="#d6dee8" />')

    axis = []
    labels = []
    values = []
    for index, item in enumerate(items):
        end_x, end_y = point(index, 1.0)
        axis.append(
            f'<line x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{end_x:.1f}" '
            f'y2="{end_y:.1f}" stroke="#d6dee8" />'
        )
        label_x, label_y = point(index, 1.18)
        anchor = "middle"
        if label_x < center_x - 10:
            anchor = "end"
        elif label_x > center_x + 10:
            anchor = "start"
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" '
            f'font-size="13" fill="#243447">{html.escape(str(item["dimension"]))}</text>'
        )
        value_scale = min(max(float(item["evidence_count"]) / max_count, 0.0), 1.0)
        values.append(point(index, value_scale))

    value_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in values)
    dots = [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#1570ef" />' for x, y in values]
    table_rows = []
    for item in items:
        status = "Sufficient" if item["sufficient"] else "Needs Improvement"
        color = "#15803d" if item["sufficient"] else "#b42318"
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item['dimension']))}</td>"
            f"<td>{int(item['evidence_count'])}</td>"
            f'<td style="color:{color};font-weight:600">{status}</td>'
            "</tr>"
        )
    return f"""
    <div style="font-family: Inter, Segoe UI, sans-serif; color:#172033;">
      <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">
        <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" />
        <text x="24" y="34" font-size="18" font-weight="700" fill="#172033">
          Evidence coverage
        </text>
        {''.join(grid)}
        {''.join(axis)}
        <polygon points="{value_points}" fill="#1570ef" fill-opacity="0.18"
          stroke="#1570ef" stroke-width="2" />
        {''.join(dots)}
        {''.join(labels)}
      </svg>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:13px">
        <thead>
          <tr style="text-align:left;color:#475569;border-bottom:1px solid #d6dee8">
            <th style="padding:8px">Dimension</th>
            <th style="padding:8px">Evidence Count</th>
            <th style="padding:8px">Status</th>
          </tr>
        </thead>
        <tbody>{''.join(table_rows)}</tbody>
      </table>
    </div>
    """


def _render_radar_chart(quality_metrics: dict[str, Any]) -> None:
    """Render coverage radar chart and summary metrics."""
    coverage = _coverage_items(quality_metrics)
    if not coverage:
        st.info("No coverage metrics are available for this report.")
        return

    score = float(quality_metrics.get("score") or 0.0)
    missing = quality_metrics.get("missing_dimensions") or []
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Coverage", f"{score:.0%}")
    covered = sum(1 for item in coverage if item["sufficient"])
    col_b.metric("Covered Dimensions", f"{covered}/{len(coverage)}")
    col_c.metric("Missing Dimensions", str(len(missing)))
    components.html(_radar_svg(coverage), height=620, scrolling=True)


def _document_filename(task_id: str) -> str:
    """Return a deterministic report document filename."""
    safe_task_id = "".join(
        char if char.isalnum() or char in {"_", "-"} else "_" for char in task_id
    )
    return f"insightagent_report_{safe_task_id}.md"


def _render_report_result(report: dict[str, Any]) -> None:
    """Render the completed report as document, chart, and quality payload."""
    task_id = str(report.get("task_id") or "task")
    markdown = str(report.get("report_markdown") or "")
    quality_metrics = dict(report.get("quality_metrics") or {})

    st.success("Research completed.")
    st.download_button(
        "Download Markdown",
        data=markdown.encode("utf-8"),
        file_name=_document_filename(task_id),
        mime="text/markdown",
        use_container_width=True,
    )

    document_tab, radar_tab, quality_tab = st.tabs(["Report", "Coverage", "Quality Data"])
    with document_tab:
        st.markdown(markdown or "No report content.")
    with radar_tab:
        _render_radar_chart(quality_metrics)
    with quality_tab:
        st.markdown("#### Citation Summary")
        st.json(citation_summary(markdown, quality_metrics.get("evidences") or []))
        st.json(quality_metrics)


def _render_failed_task(report_box: Any, status: dict[str, Any]) -> None:
    issues = [str(issue) for issue in status.get("issues") or [] if str(issue).strip()]
    message = "Task failed."
    if issues:
        message = f"{message} {issues[0]}"
    report_box.error(message)


def _render_api_failure(status_box: Any, error: Exception) -> None:
    with status_box.container():
        _render_status_panel(
            {
                "status": "FAILED",
                "current_stage": "failed",
                "stage_label": "Backend request failed",
                "progress": 1.0,
                "estimated_remaining_seconds": 0,
                "issues": [str(error)],
            }
        )


def _poll_timed_out(started_at: float, now: float, max_seconds: int) -> bool:
    return now - started_at >= max_seconds


def main() -> None:
    st.set_page_config(page_title="InsightAgent", layout="wide")
    st.title("InsightAgent Competitive Analysis")

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        with st.form("task_form"):
            query = st.text_input("Market or product area", "AI coding assistant market")
            competitors_text = st.text_input("Competitors", "")
            dimensions_text = st.text_input("Dimensions", "")
            submitted = st.form_submit_button("Start Research")
        report_box = st.empty()

    with right:
        status_box = st.empty()
        with status_box.container():
            _render_status_panel(None)

    if submitted:
        competitors = _split_csv(competitors_text)
        dimensions = _split_csv(dimensions_text)
        try:
            task_id = _create_task(query, competitors, dimensions)
            latest_status: dict[str, Any] | None = None
            poll_started = time.monotonic()
            while True:
                try:
                    latest_status = _get_status(task_id)
                except httpx.HTTPStatusError as exc:
                    if _is_transient_http_error(exc) and not _poll_timed_out(
                        poll_started,
                        time.monotonic(),
                        MAX_POLL_SECONDS,
                    ):
                        report_box.warning("Backend is busy. Retrying status poll...")
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue
                    raise
                except (httpx.TimeoutException, httpx.TransportError):
                    if not _poll_timed_out(poll_started, time.monotonic(), MAX_POLL_SECONDS):
                        report_box.warning("Backend status poll failed. Retrying...")
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue
                    raise
                with status_box.container():
                    _render_status_panel(latest_status)
                latest_state = str(_require_field(latest_status, "status"))
                if latest_state in FINAL_STATUSES:
                    break
                if _poll_timed_out(poll_started, time.monotonic(), MAX_POLL_SECONDS):
                    report_box.warning("Task is still running. Refresh later to continue polling.")
                    break
                time.sleep(POLL_INTERVAL_SECONDS)
            if latest_status and str(_require_field(latest_status, "status")) == "FAILED":
                _render_failed_task(report_box, latest_status)
            elif latest_status and str(_require_field(latest_status, "status")) in FINAL_STATUSES:
                try:
                    report = _get_report_with_retries(task_id)
                except ReportNotReadyError as exc:
                    report_box.info(str(exc))
                else:
                    with report_box.container():
                        _render_report_result(report)
        except (httpx.HTTPError, ValueError) as exc:
            report_box.error(f"Backend request failed: {exc}")
            _render_api_failure(status_box, exc)


if __name__ == "__main__":
    main()
