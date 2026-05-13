"""Streamlit frontend for InsightAgent v4.

Thin orchestrator: layout, session-state init, and state routing.
All component logic lives in frontend/components/.
"""

from typing import Any

import httpx
import streamlit as st

from frontend.components.report_viewer import render_report_view
from frontend.components.status_panel import poll_status_fragment
from frontend.components.task_form import render_task_form
from frontend.i18n import t
from frontend.theme import inject_custom_css
from frontend.utils import (
    api_create_task,
    api_health_check,
    init_session_state,
)

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title="InsightAgent",
        page_icon=":material/search:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()
    init_session_state()

    _render_sidebar()
    _render_header()

    task_id = st.session_state.get("task_id")

    if not task_id:
        _render_idle_state()
    else:
        _render_active_state()


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------


def _render_header() -> None:
    h1, h2 = st.columns([6, 1])
    with h1:
        st.markdown(
            '<div class="brand-header">'
            '<span class="brand-icon">:material/search:</span> '
            '<span class="brand-title">InsightAgent</span>'
            f'<span class="brand-subtitle">{t("brand_subtitle")}</span>'
            "</div>",
            unsafe_allow_html=True,
        )
    with h2:
        health = st.session_state.get("health_status")
        if health and health.get("status") == "ok":
            badge = f":green_circle: {t('connected')}"
        elif health:
            badge = f":orange_circle: {t('degraded')}"
        else:
            badge = f":black_circle: {t('offline')}"
        st.markdown(
            f'<div class="health-badge">{badge}</div>',
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------


def _render_sidebar() -> None:
    with st.sidebar:
        # Language toggle
        lang = st.session_state.get("lang", "en")
        new_lang = "zh" if lang == "en" else "en"
        if st.button(
            t("switch_lang"),
            key="lang_toggle",
            help=f"{t('language')} / 切换语言",
            use_container_width=True,
        ):
            st.session_state.lang = new_lang
            st.rerun()

        st.divider()
        st.markdown(f"### {t('task_history')}")

        history = st.session_state.get("task_history") or []
        if history:
            for entry in reversed(history[-10:]):
                hid = entry["task_id"]
                with st.container(border=True):
                    st.caption(entry["query"][:60])
                    st.caption(f"`{hid[:16]}...`")
                    status = entry.get("status", "")
                    status_icon = {
                        "COMPLETED": ":white_check_mark:",
                        "COMPLETED_WITH_WARNINGS": ":warning:",
                        "FAILED": ":x:",
                        "RUNNING": ":arrows_counterclockwise:",
                        "PENDING": ":pause_button:",
                    }.get(status, ":clipboard:")
                    st.caption(f"{status_icon} {status}")
                    if st.button(t("restore"), key=f"hist_{hid}"):
                        st.session_state.task_id = hid
                        st.session_state.polling_active = True
                        st.session_state.task_completed = False
                        st.session_state.report_data = None
                        st.query_params["task_id"] = hid
                        st.rerun()
        else:
            st.caption(t("no_previous_tasks"))

        st.divider()
        st.markdown(f"### {t('about')}")
        st.caption("**InsightAgent** v4.0")
        st.caption(t("about_desc"))
        st.caption("FastAPI + LangGraph + Streamlit")

        if st.button(
            f":arrows_counterclockwise: {t('check_connection')}",
            use_container_width=True,
        ):
            result = api_health_check()
            st.session_state.health_status = result
            st.session_state.health_checked = True
            if result:
                st.toast(t("api_connected"), icon=":material/check:")
            else:
                st.toast(t("api_unreachable"), icon=":material/error:")
            st.rerun()


# ------------------------------------------------------------------
# State routing
# ------------------------------------------------------------------


def _render_idle_state() -> None:
    """No active task: show form centered."""
    _, center, _ = st.columns([1, 2, 1])
    with center:
        form_data = render_task_form()
        if form_data:
            _handle_submit(form_data)


def _render_active_state() -> None:
    """Active task: form left, status/report right."""
    left, right = st.columns([1, 1], gap="large")

    with left:
        form_data = render_task_form()
        if form_data:
            _handle_submit(form_data)

    with right:
        if st.session_state.get("task_completed") and st.session_state.get(
            "report_data"
        ):
            render_report_view(st.session_state.report_data)
        elif st.session_state.get("task_completed") and st.session_state.get(
            "last_error"
        ):
            st.error(st.session_state.last_error)
            if st.button(t("try_again"), key="retry_report"):
                _retry_fetch_report()
        elif st.session_state.get("last_error"):
            st.error(st.session_state.last_error)
        elif st.session_state.get("task_status"):
            status = st.session_state.last_status
            if status and status.get("status") == "FAILED":
                issues = [
                    str(i) for i in status.get("issues") or [] if str(i).strip()
                ]
                msg = t("task_failed")
                if issues:
                    msg = f"{msg} {issues[0]}"
                st.error(msg)
            else:
                poll_status_fragment()
        else:
            poll_status_fragment()


# ------------------------------------------------------------------
# Handlers
# ------------------------------------------------------------------


def _handle_submit(form_data: dict[str, Any]) -> None:
    try:
        task_id = api_create_task(
            form_data["query"],
            form_data["competitors"],
            form_data["dimensions"],
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            st.error(t("system_at_capacity"))
        elif exc.response.status_code == 422:
            detail = t("validation_error")
            try:
                detail = str(exc.response.json().get("detail", detail))
            except Exception:
                pass
            st.error(f"{t('invalid_input')} {detail}")
        else:
            st.error(f"{t('submission_failed')} HTTP {exc.response.status_code}")
        return
    except Exception as exc:
        st.error(f"{t('failed_create_task')} {exc}")
        return

    st.session_state.task_id = task_id
    st.session_state.task_status = "PENDING"
    st.session_state.task_completed = False
    st.session_state.polling_active = True
    st.session_state.report_data = None
    st.session_state.last_error = None
    st.session_state.consecutive_failures = 0
    st.session_state.report_retry_count = 0
    st.query_params["task_id"] = task_id

    history = st.session_state.get("task_history") or []
    history.append(
        {
            "task_id": task_id,
            "query": form_data["query"],
            "status": "PENDING",
        }
    )
    st.session_state.task_history = history

    st.toast(t("task_submitted_toast"), icon=":material/rocket_launch:")
    st.rerun()


def _retry_fetch_report() -> None:
    task_id = st.session_state.get("task_id")
    if not task_id:
        return
    try:
        from frontend.utils import api_get_report_with_retries

        report = api_get_report_with_retries(task_id)
        st.session_state.report_data = report
        st.session_state.last_error = None
        st.rerun()
    except Exception as exc:
        st.session_state.last_error = str(exc)


if __name__ == "__main__":
    main()
