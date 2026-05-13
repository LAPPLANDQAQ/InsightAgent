"""Shared utilities for the InsightAgent frontend.

API helpers, session-state init, formatting, and constants — no Streamlit
rendering imports, so this module is testable without a Streamlit runtime.
"""

import os
import time
from typing import Any

import httpx


def get_api_base() -> str:
    """Return the configured backend API base URL."""
    return os.getenv("INSIGHT_API_BASE", "http://127.0.0.1:8000").rstrip("/")


API_BASE = get_api_base()
POLL_INTERVAL_SECONDS = 2
MAX_POLL_SECONDS = int(os.getenv("INSIGHT_FRONTEND_MAX_POLL_SECONDS", "900"))
MAX_CONSECUTIVE_POLL_FAILURES = 15
REPORT_RETRY_ATTEMPTS = 3
REPORT_RETRY_INTERVAL_SECONDS = 1
TRANSIENT_STATUS_CODES = {429, 503}
FINAL_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}

STAGES: list[tuple[str, str]] = [
    ("queued", "Queued"),
    ("planner", "Planning"),
    ("researcher", "Researching"),
    ("sufficiency_check", "Checking Evidence Sufficiency"),
    ("analyst", "Analyzing"),
    ("writer", "Writing Report"),
    ("critic", "Reviewing"),
    ("finalize", "Finalizing"),
]

HTTP_CLIENT = httpx.Client(
    timeout=20.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)

SESSION_DEFAULTS: dict[str, Any] = {
    "task_id": None,
    "task_status": None,
    "task_completed": False,
    "current_stage": None,
    "report_data": None,
    "last_status": None,
    "polling_active": False,
    "last_error": None,
    "consecutive_failures": 0,
    "task_history": [],
    "health_status": None,
    "health_checked": False,
    "report_retry_count": 0,
    "lang": "en",
    "form_disabled": False,
}


class ReportNotReadyError(RuntimeError):
    """Raised when the API reports that a task has no report yet."""


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


def _format_eta(seconds: int | None, lang: str = "en") -> str:
    from frontend.i18n import t as _t

    if seconds is None:
        return _t("estimating", lang)
    if seconds <= 0:
        return _t("done", lang)
    minutes, remainder = divmod(seconds, 60)
    about = _t("about_time", lang)
    if minutes:
        return f"{about} {minutes}m {remainder}s"
    return f"{about} {remainder}s"


def _stage_index(stage: str | None) -> int:
    if not stage:
        return -1
    for index, (key, _) in enumerate(STAGES):
        if key == stage:
            return index
    return -1


def _is_transient_http_error(exc: httpx.HTTPStatusError) -> bool:
    return exc.response.status_code in TRANSIENT_STATUS_CODES


def _require_field(payload: dict[str, Any], field: str) -> Any:
    if field not in payload:
        raise ValueError(f"missing field: {field}")
    return payload[field]


def _poll_timed_out(started_at: float, now: float, max_seconds: int) -> bool:
    return now - started_at >= max_seconds


def _split_csv(text: str) -> list[str]:
    if not text.strip():
        return []
    return [
        item.strip()
        for item in text.replace("，", ",").split(",")
        if item.strip()
    ]


def _document_filename(task_id: str) -> str:
    safe_task_id = "".join(
        char if char.isalnum() or char in {"_", "-"} else "_" for char in task_id
    )
    return f"insightagent_report_{safe_task_id}.md"


# ------------------------------------------------------------------
# API helpers
# ------------------------------------------------------------------


def api_create_task(
    query: str,
    competitors: list[str],
    dimensions: list[str],
    client: httpx.Client | None = None,
) -> str:
    client = client or HTTP_CLIENT
    response = client.post(
        f"{get_api_base()}/api/tasks",
        json={"query": query, "competitors": competitors, "dimensions": dimensions},
    )
    response.raise_for_status()
    return _require_field(response.json(), "task_id")


def api_get_status(task_id: str, client: httpx.Client | None = None) -> dict[str, Any]:
    client = client or HTTP_CLIENT
    response = client.get(f"{get_api_base()}/api/tasks/{task_id}")
    response.raise_for_status()
    return response.json()


def api_get_report(task_id: str, client: httpx.Client | None = None) -> dict[str, Any]:
    client = client or HTTP_CLIENT
    response = client.get(f"{get_api_base()}/api/tasks/{task_id}/report")
    if response.status_code == 404:
        raise ReportNotReadyError("Report is not ready yet. Please refresh later.")
    response.raise_for_status()
    return response.json()


def api_get_report_with_retries(task_id: str) -> dict[str, Any]:
    for _ in range(REPORT_RETRY_ATTEMPTS):
        try:
            return api_get_report(task_id)
        except ReportNotReadyError:
            time.sleep(REPORT_RETRY_INTERVAL_SECONDS)
    raise ReportNotReadyError(
        "Report is still not ready after several attempts. Please refresh later."
    )


def api_health_check(client: httpx.Client | None = None) -> dict[str, Any] | None:
    client = client or HTTP_CLIENT
    try:
        response = client.get(f"{get_api_base()}/healthz", timeout=5.0)
        return response.json() if response.is_success else None
    except Exception:
        return None


# ------------------------------------------------------------------
# Session state helpers
# ------------------------------------------------------------------


def init_session_state() -> None:
    import streamlit as st

    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default

    params = st.query_params
    if "task_id" in params and not st.session_state.task_id:
        st.session_state.task_id = str(params["task_id"])
        st.session_state.polling_active = True
        st.session_state.task_completed = False


def clear_task_state() -> None:
    import streamlit as st

    for key in (
        "task_id",
        "task_status",
        "task_completed",
        "current_stage",
        "report_data",
        "last_status",
        "polling_active",
        "last_error",
        "consecutive_failures",
        "report_retry_count",
    ):
        if key in st.session_state:
            del st.session_state[key]
    st.query_params.clear()


# ------------------------------------------------------------------
# SVG radar chart (preserved as fallback)
# ------------------------------------------------------------------


def _radar_svg(items: list[dict[str, Any]], lang: str = "en") -> str:
    import html
    import math

    from frontend.i18n import t as _t

    count = len(items)
    if count == 0:
        return f"<p>{_t('no_coverage_data', lang)}</p>"
    width, height = 620, 460
    center_x, center_y = width / 2, height / 2
    radius = 145
    max_count = max(item["evidence_count"] for item in items) + 1

    def point(index: int, scale: float) -> tuple[float, float]:
        angle = -math.pi / 2 + (2 * math.pi * index / count)
        x = center_x + math.cos(angle) * radius * scale
        y = center_y + math.sin(angle) * radius * scale
        return x, y

    grid = []
    for scale in (0.25, 0.5, 0.75, 1.0):
        points = " ".join(
            f"{x:.1f},{y:.1f}" for x, y in (point(i, scale) for i in range(count))
        )
        grid.append(
            f'<polygon points="{points}" fill="none" stroke="#d6dee8" />'
        )

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
        status = _t("sufficient", lang) if item["sufficient"] else _t("needs_improvement", lang)
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
          {_t('chart_evidence', lang)} {_t('tab_coverage', lang).lower()}
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
            <th style="padding:8px">{_t('col_dimension', lang)}</th>
            <th style="padding:8px">{_t('col_evidence_count', lang)}</th>
            <th style="padding:8px">{_t('col_status', lang)}</th>
          </tr>
        </thead>
        <tbody>{''.join(table_rows)}</tbody>
      </table>
    </div>
    """


def _coverage_items(quality_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    coverage = quality_metrics.get("coverage") or []
    if not isinstance(coverage, list):
        return []
    items: list[dict[str, Any]] = []
    for item in coverage:
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
