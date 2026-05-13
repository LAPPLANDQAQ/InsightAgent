"""Chinese/English translations for the InsightAgent frontend."""

import streamlit as st

TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Header ---
    "brand_subtitle": {
        "en": "Competitive Analysis",
        "zh": "竞品分析",
    },
    "connected": {"en": "Connected", "zh": "已连接"},
    "degraded": {"en": "Degraded", "zh": "性能降级"},
    "offline": {"en": "Offline", "zh": "离线"},
    # --- Sidebar ---
    "task_history": {"en": "Task History", "zh": "任务历史"},
    "no_previous_tasks": {
        "en": "No previous tasks in this session.",
        "zh": "本次会话暂无历史任务",
    },
    "restore": {"en": "Restore", "zh": "恢复"},
    "about": {"en": "About", "zh": "关于"},
    "about_desc": {
        "en": "Competitive Analysis AI Agent",
        "zh": "竞品分析 AI 智能体",
    },
    "check_connection": {"en": "Check Connection", "zh": "检查连接"},
    "api_connected": {"en": "API connected", "zh": "API 已连接"},
    "api_unreachable": {"en": "API unreachable", "zh": "API 无法访问"},
    # --- Language toggle ---
    "language": {"en": "Language", "zh": "语言"},
    "switch_lang": {"en": "中文", "zh": "English"},
    # --- Task form ---
    "new_analysis": {"en": "New Competitive Analysis", "zh": "新建竞品分析"},
    "new_analysis_desc": {
        "en": "Describe the market or product area you want to research.",
        "zh": "描述您想研究的市场或产品领域",
    },
    "form_query_label": {"en": "Market or Product Area", "zh": "市场或产品领域"},
    "form_query_placeholder": {
        "en": "e.g., AI coding assistant market",
        "zh": "例如：AI 编程助手市场",
    },
    "form_query_help": {"en": "Minimum 2 characters.", "zh": "至少 2 个字符"},
    "form_competitors_label": {"en": "Competitors", "zh": "竞品"},
    "form_competitors_placeholder": {
        "en": "e.g., Cursor, GitHub Copilot, Windsurf",
        "zh": "例如：Cursor, GitHub Copilot, Windsurf",
    },
    "form_competitors_help": {
        "en": (
            "Comma-separated list of competitors. Optional — "
            "InsightAgent will discover competitors if blank."
        ),
        "zh": "逗号分隔的竞品列表。可选 — 留空将由系统自动发现竞品",
    },
    "form_dimensions_label": {"en": "Analysis Dimensions", "zh": "分析维度"},
    "form_dimensions_placeholder": {
        "en": "e.g., pricing, features, ecosystem, market share",
        "zh": "例如：定价、功能、生态、市场份额",
    },
    "form_dimensions_help": {
        "en": (
            "Comma-separated analysis dimensions. Optional — "
            "InsightAgent will infer dimensions if blank."
        ),
        "zh": "逗号分隔的分析维度。可选 — 留空将由系统自动推断维度",
    },
    "query_too_short": {
        "en": "Query must be at least 2 characters.",
        "zh": "查询内容至少需要 2 个字符",
    },
    "start_research": {"en": "Start Research", "zh": "开始分析"},
    "new_task": {"en": "New Task", "zh": "新建任务"},
    # --- Status panel ---
    "backend_busy": {
        "en": "Backend is busy. Retrying status poll automatically...",
        "zh": "后端繁忙，正在自动重试状态查询...",
    },
    "connection_issue": {
        "en": "Connection issue. Retrying...",
        "zh": "连接异常，正在重试...",
    },
    "task_not_found": {
        "en": "Task not found. It may have been removed.",
        "zh": "任务未找到，可能已被删除",
    },
    "task_not_found_404": {
        "en": "Task not found (404)",
        "zh": "任务未找到 (404)",
    },
    "unexpected_error": {"en": "Unexpected error:", "zh": "未知错误："},
    "backend_unreachable": {
        "en": (
            "Backend appears unreachable after several attempts. "
            "Check that the API server is running, then start a new task."
        ),
        "zh": "后端多次尝试后仍无法访问。请检查 API 服务是否运行，然后新建任务",
    },
    "polling_timed_out": {
        "en": "Polling timed out. The task may still be running. Refresh or start a new task.",
        "zh": "轮询超时。任务可能仍在运行。请刷新页面或新建任务",
    },
    "pipeline_stages": {"en": "Pipeline Stages", "zh": "流水线阶段"},
    "overall": {"en": "Overall", "zh": "总体进度"},
    "status": {"en": "Status", "zh": "状态"},
    "stage": {"en": "Stage", "zh": "阶段"},
    "eta": {"en": "ETA", "zh": "预计剩余"},
    "active": {"en": "active", "zh": "进行中"},
    "issues_label": {"en": "Issues", "zh": "问题"},
    # --- Stage display names ---
    "stage_queued": {"en": "Queued", "zh": "排队中"},
    "stage_planner": {"en": "Planning", "zh": "规划中"},
    "stage_researcher": {"en": "Researching", "zh": "调研中"},
    "stage_sufficiency_check": {
        "en": "Checking Evidence Sufficiency",
        "zh": "检查证据充分性",
    },
    "stage_analyst": {"en": "Analyzing", "zh": "分析中"},
    "stage_writer": {"en": "Writing Report", "zh": "撰写报告"},
    "stage_critic": {"en": "Reviewing", "zh": "审核中"},
    "stage_finalize": {"en": "Finalizing", "zh": "最终处理"},
    # --- Report viewer ---
    "research_completed": {
        "en": "Research completed successfully.",
        "zh": "分析已成功完成",
    },
    "download_markdown": {"en": "Download Markdown", "zh": "下载 Markdown"},
    "tab_report": {"en": "Report", "zh": "报告"},
    "tab_coverage": {"en": "Coverage", "zh": "覆盖度"},
    "tab_quality_data": {"en": "Quality Data", "zh": "质量数据"},
    "tab_evidence": {"en": "Evidence", "zh": "证据"},
    "no_report_content": {
        "en": "No report content was generated.",
        "zh": "未生成报告内容",
    },
    "total_citations": {"en": "Total Citations", "zh": "引用总数"},
    "citation_density": {"en": "Citation Density", "zh": "引用密度"},
    "missing_references": {"en": "Missing References", "zh": "缺失引用"},
    "missing_evidence_refs": {
        "en": "Missing evidence references:",
        "zh": "缺失证据引用：",
    },
    "raw_quality_metrics": {"en": "Raw Quality Metrics", "zh": "原始质量指标"},
    "col_evidence_id": {"en": "Evidence ID", "zh": "证据 ID"},
    "col_source": {"en": "Source", "zh": "来源"},
    "col_relevance": {"en": "Relevance", "zh": "相关度"},
    "no_evidence_records": {
        "en": "No evidence records in this report.",
        "zh": "此报告中没有证据记录",
    },
    # --- Coverage charts ---
    "no_coverage_metrics": {
        "en": "No coverage metrics are available for this report.",
        "zh": "此报告暂无覆盖度指标",
    },
    "coverage_score": {"en": "Coverage Score", "zh": "覆盖度评分"},
    "sufficient_dimensions": {
        "en": "Sufficient Dimensions",
        "zh": "充分覆盖维度",
    },
    "total_evidence": {"en": "Total Evidence", "zh": "证据总数"},
    "missing_dimensions": {"en": "Missing Dimensions", "zh": "缺失维度"},
    "dimension_details": {"en": "Dimension Details", "zh": "维度详情"},
    "sufficient": {"en": "Sufficient", "zh": "充分"},
    "needs_improvement": {"en": "Needs Improvement", "zh": "需改进"},
    "col_dimension": {"en": "Dimension", "zh": "维度"},
    "col_evidence_count": {"en": "Evidence Count", "zh": "证据数量"},
    "col_status": {"en": "Status", "zh": "状态"},
    "chart_evidence": {"en": "Evidence", "zh": "证据"},
    "chart_average": {"en": "Average", "zh": "平均值"},
    "no_coverage_data": {"en": "No coverage data.", "zh": "无覆盖度数据"},
    # --- Formatting ---
    "estimating": {"en": "Estimating", "zh": "评估中"},
    "done": {"en": "Done", "zh": "完成"},
    "about_time": {"en": "About", "zh": "约"},
    # --- Task states ---
    "task_failed": {"en": "Task failed.", "zh": "任务失败"},
    "try_again": {"en": "Try Again", "zh": "重试"},
    "system_at_capacity": {
        "en": "System is at capacity. Please wait 30 seconds and try again.",
        "zh": "系统繁忙，请等待 30 秒后重试",
    },
    "validation_error": {"en": "Validation error", "zh": "输入验证错误"},
    "invalid_input": {"en": "Invalid input:", "zh": "输入无效："},
    "submission_failed": {"en": "Submission failed:", "zh": "提交失败："},
    "failed_create_task": {
        "en": "Failed to create task:",
        "zh": "创建任务失败：",
    },
    "research_completed_toast": {
        "en": "Research completed!",
        "zh": "分析完成！",
    },
    "research_failed_toast": {
        "en": "Research task failed.",
        "zh": "分析任务失败",
    },
    "task_submitted_toast": {
        "en": "Task submitted!",
        "zh": "任务已提交！",
    },
    # --- Report retry ---
    "report_not_ready": {
        "en": "Report is not ready yet. Please refresh later.",
        "zh": "报告尚未就绪，请稍后刷新",
    },
    "report_still_not_ready": {
        "en": "Report is still not ready after several attempts. Please refresh later.",
        "zh": "多次尝试后报告仍未就绪，请稍后刷新",
    },
}


def t(key: str, lang: str | None = None) -> str:
    """Return the translation for *key* in the current language.

    Reads ``st.session_state.lang`` if *lang* is not explicitly passed.
    Falls back to English when a key or language is missing.
    """
    if lang is None:
        lang = st.session_state.get("lang", "en")
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))
