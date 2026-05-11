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

API_BASE = os.getenv("INSIGHT_API_BASE", "http://127.0.0.1:8000")
HTTP_CLIENT = httpx.Client(
    timeout=20.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)
FINAL_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}
STAGES = [
    ("planner", "规划"),
    ("researcher", "调研"),
    ("analyst", "分析"),
    ("writer", "报告"),
    ("critic", "质检"),
]


def _format_eta(seconds: int | None) -> str:
    """Format estimated remaining time."""
    if seconds is None:
        return "估算中"
    if seconds <= 0:
        return "已完成"
    minutes, remainder = divmod(seconds, 60)
    if minutes:
        return f"约 {minutes} 分 {remainder} 秒"
    return f"约 {remainder} 秒"


def _stage_index(stage: str | None) -> int:
    """Return the current stage index."""
    for index, (name, _) in enumerate(STAGES):
        if name == stage:
            return index
    return -1


def _render_status_panel(status: dict[str, Any] | None) -> None:
    """Render the right-side status visualization."""
    st.subheader("运行状态")
    if status is None:
        st.info("等待创建任务")
        st.progress(0.0)
        for _, label in STAGES:
            st.caption(f"○ {label}")
        return

    progress = float(status.get("progress") or 0.0)
    current_stage = status.get("current_stage")
    current_index = _stage_index(current_stage)
    st.metric("当前状态", status.get("status", "UNKNOWN"))
    st.metric("当前阶段", status.get("stage_label") or current_stage or "未知")
    st.metric("预计剩余", _format_eta(status.get("estimated_remaining_seconds")))
    st.progress(progress, text=f"{progress:.0%}")

    st.markdown("#### 阶段")
    for index, (stage, label) in enumerate(STAGES):
        if index < current_index or status.get("status") in FINAL_STATUSES:
            marker = "●"
        elif index == current_index:
            marker = "◐"
        else:
            marker = "○"
        st.caption(f"{marker} {label} · `{stage}`")

    issues = status.get("issues") or []
    if issues:
        st.markdown("#### 提示")
        for issue in issues[:5]:
            st.warning(str(issue))


def _create_task(query: str, competitors: list[str], dimensions: list[str]) -> str:
    """Create a task through the API."""
    response = HTTP_CLIENT.post(
        f"{API_BASE}/api/tasks",
        json={"query": query, "competitors": competitors, "dimensions": dimensions},
    )
    response.raise_for_status()
    return str(response.json()["task_id"])


def _get_status(task_id: str) -> dict[str, Any]:
    """Fetch task status."""
    response = HTTP_CLIENT.get(f"{API_BASE}/api/tasks/{task_id}")
    response.raise_for_status()
    return response.json()


def _get_report(task_id: str) -> dict[str, Any]:
    """Fetch task report."""
    response = HTTP_CLIENT.get(f"{API_BASE}/api/tasks/{task_id}/report")
    response.raise_for_status()
    return response.json()


def _split_csv(text: str) -> list[str]:
    """Split comma separated input into normalized values."""
    return [item.strip() for item in text.replace("，", ",").split(",") if item.strip()]


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
        evidence_count = int(item.get("evidence_count") or 0)
        items.append(
            {
                "dimension": dimension,
                "evidence_count": evidence_count,
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

    grid_polygons = []
    for scale in (0.25, 0.5, 0.75, 1.0):
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, scale) for i in range(count)))
        grid_polygons.append(
            f'<polygon points="{points}" fill="none" stroke="#d6dee8" stroke-width="1" />'
        )

    axis_lines = []
    labels = []
    values = []
    for index, item in enumerate(items):
        end_x, end_y = point(index, 1.0)
        axis_lines.append(
            f'<line x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{end_x:.1f}" '
            f'y2="{end_y:.1f}" stroke="#d6dee8" stroke-width="1" />'
        )
        label_x, label_y = point(index, 1.18)
        anchor = "middle"
        if label_x < center_x - 10:
            anchor = "end"
        elif label_x > center_x + 10:
            anchor = "start"
        escaped_label = html.escape(str(item["dimension"]))
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" '
            f'font-size="13" fill="#243447">{escaped_label}</text>'
        )
        value_scale = min(max(float(item["evidence_count"]) / max_count, 0.0), 1.0)
        values.append(point(index, value_scale))

    value_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in values)
    dots = []
    for x, y in values:
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#1570ef" />')

    legend_rows = []
    for item in items:
        status = "充分" if item["sufficient"] else "待补强"
        color = "#15803d" if item["sufficient"] else "#b42318"
        legend_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item['dimension']))}</td>"
            f"<td>{item['evidence_count']}</td>"
            f'<td style="color:{color};font-weight:600">{status}</td>'
            "</tr>"
        )

    title = "维度证据覆盖雷达图"
    subtitle = "按每个维度的证据数量归一化展示，外圈代表本次任务中的最高证据数。"
    return f"""
    <div style="font-family: Inter, Segoe UI, sans-serif; color:#172033;">
      <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">
        <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" />
        <text x="24" y="34" font-size="18" font-weight="700" fill="#172033">{title}</text>
        <text x="24" y="58" font-size="12" fill="#64748b">{subtitle}</text>
        {''.join(grid_polygons)}
        {''.join(axis_lines)}
        <polygon points="{value_points}" fill="#1570ef" fill-opacity="0.18"
          stroke="#1570ef" stroke-width="2" />
        {''.join(dots)}
        {''.join(labels)}
      </svg>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:13px">
        <thead>
          <tr style="text-align:left;color:#475569;border-bottom:1px solid #d6dee8">
            <th style="padding:8px">维度</th>
            <th style="padding:8px">证据数</th>
            <th style="padding:8px">状态</th>
          </tr>
        </thead>
        <tbody>{''.join(legend_rows)}</tbody>
      </table>
    </div>
    """


def _render_radar_chart(quality_metrics: dict[str, Any]) -> None:
    """Render coverage radar chart and summary metrics."""
    coverage = _coverage_items(quality_metrics)
    if not coverage:
        st.info("暂无维度覆盖数据，完成调研后会在这里生成雷达图。")
        return

    score = float(quality_metrics.get("score") or 0.0)
    missing = quality_metrics.get("missing_dimensions") or []
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("整体覆盖率", f"{score:.0%}")
    col_b.metric("覆盖维度", f"{sum(1 for item in coverage if item['sufficient'])}/{len(coverage)}")
    col_c.metric("待补强维度", str(len(missing)))
    components.html(_radar_svg(coverage), height=560, scrolling=True)


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

    st.success("调研完成，已生成结构化文档和维度覆盖雷达图。")
    st.download_button(
        "下载调研文档 Markdown",
        data=markdown.encode("utf-8"),
        file_name=_document_filename(task_id),
        mime="text/markdown",
        use_container_width=True,
    )

    document_tab, radar_tab, quality_tab = st.tabs(["调研文档", "雷达图", "质量数据"])
    with document_tab:
        st.markdown(markdown or "暂无报告内容。")
    with radar_tab:
        _render_radar_chart(quality_metrics)
    with quality_tab:
        st.markdown("#### 引用摘要")
        st.json(citation_summary(markdown, quality_metrics.get("evidences") or []))
        st.json(quality_metrics)


st.set_page_config(page_title="InsightAgent", layout="wide")
st.title("InsightAgent 多 Agent 竞品分析")

left, right = st.columns([2.2, 1], gap="large")

with left:
    with st.form("task_form"):
        query = st.text_input("赛道或产品方向", "AI 编程助手赛道")
        competitors_text = st.text_input("指定竞品，使用逗号分隔", "")
        dimensions_text = st.text_input("指定分析维度，使用逗号分隔", "")
        submitted = st.form_submit_button("开始调研")
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
        while True:
            latest_status = _get_status(task_id)
            with status_box.container():
                _render_status_panel(latest_status)
            if latest_status["status"] in FINAL_STATUSES:
                break
            time.sleep(2)
        if latest_status["status"] == "FAILED":
            report_box.error("任务失败，请查看右侧提示或后端日志。")
        else:
            report = _get_report(task_id)
            with report_box.container():
                _render_report_result(report)
    except httpx.HTTPError as exc:
        report_box.error(f"请求后端失败：{exc}")
        with status_box.container():
            _render_status_panel(
                {
                    "status": "FAILED",
                    "current_stage": "failed",
                    "stage_label": "请求失败",
                    "progress": 1.0,
                    "estimated_remaining_seconds": 0,
                    "issues": [str(exc)],
                }
            )
