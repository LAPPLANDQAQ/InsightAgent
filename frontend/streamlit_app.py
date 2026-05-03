"""Streamlit frontend for InsightAgent."""

import os
import time
from typing import Any

import httpx
import streamlit as st

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
    """Format estimated remaining time.

    Args:
        seconds: Remaining seconds.

    Returns:
        Human-readable remaining time.
    """
    if seconds is None:
        return "估算中"
    if seconds <= 0:
        return "已完成"
    minutes, remainder = divmod(seconds, 60)
    if minutes:
        return f"约 {minutes} 分 {remainder} 秒"
    return f"约 {remainder} 秒"


def _stage_index(stage: str | None) -> int:
    """Return the current stage index.

    Args:
        stage: Current stage name.

    Returns:
        Zero-based stage index, or -1 when unknown.
    """
    for index, (name, _) in enumerate(STAGES):
        if name == stage:
            return index
    return -1


def _render_status_panel(status: dict[str, Any] | None) -> None:
    """Render the right-side status visualization.

    Args:
        status: Task status payload from API.
    """
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
            marker = "◉"
        else:
            marker = "○"
        st.caption(f"{marker} {label} · `{stage}`")

    issues = status.get("issues") or []
    if issues:
        st.markdown("#### 提示")
        for issue in issues[:5]:
            st.warning(str(issue))


def _create_task(query: str, competitors: list[str], dimensions: list[str]) -> str:
    """Create a task through the API.

    Args:
        query: User query.
        competitors: Requested competitors.
        dimensions: Requested dimensions.

    Returns:
        Created task id.
    """
    response = HTTP_CLIENT.post(
        f"{API_BASE}/api/tasks",
        json={"query": query, "competitors": competitors, "dimensions": dimensions},
    )
    response.raise_for_status()
    return str(response.json()["task_id"])


def _get_status(task_id: str) -> dict[str, Any]:
    """Fetch task status.

    Args:
        task_id: Task identifier.

    Returns:
        Status payload.
    """
    response = HTTP_CLIENT.get(f"{API_BASE}/api/tasks/{task_id}")
    response.raise_for_status()
    return response.json()


def _get_report(task_id: str) -> dict[str, Any]:
    """Fetch task report.

    Args:
        task_id: Task identifier.

    Returns:
        Report payload.
    """
    response = HTTP_CLIENT.get(f"{API_BASE}/api/tasks/{task_id}/report")
    response.raise_for_status()
    return response.json()


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
    competitors = [item.strip() for item in competitors_text.split(",") if item.strip()]
    dimensions = [item.strip() for item in dimensions_text.split(",") if item.strip()]
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
            report_box.markdown(report["report_markdown"])
            report_box.json(report.get("quality_metrics", {}))
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
