"""Streamlit frontend for InsightAgent."""

import time

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="InsightAgent", layout="wide")
st.title("InsightAgent 多 Agent 竞品分析")

with st.form("task_form"):
    query = st.text_input("赛道或产品方向", "AI 编程助手赛道")
    competitors_text = st.text_input("指定竞品，使用逗号分隔", "")
    dimensions_text = st.text_input("指定分析维度，使用逗号分隔", "")
    submitted = st.form_submit_button("开始调研")

if submitted:
    competitors = [item.strip() for item in competitors_text.split(",") if item.strip()]
    dimensions = [item.strip() for item in dimensions_text.split(",") if item.strip()]
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            f"{API_BASE}/api/tasks",
            json={"query": query, "competitors": competitors, "dimensions": dimensions},
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
    status_box = st.empty()
    while True:
        with httpx.Client(timeout=20.0) as client:
            status = client.get(f"{API_BASE}/api/tasks/{task_id}").json()
        status_box.info(f"状态：{status['status']} | 阶段：{status.get('current_stage')}")
        if status["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}:
            break
        time.sleep(2)
    if status["status"] == "FAILED":
        st.error("任务失败")
    else:
        with httpx.Client(timeout=20.0) as client:
            report = client.get(f"{API_BASE}/api/tasks/{task_id}/report").json()
        st.markdown(report["report_markdown"])
        st.json(report.get("quality_metrics", {}))
