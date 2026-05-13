"""Polling status panel using Streamlit fragment auto-refresh."""

from typing import Any

import httpx
import streamlit as st

from frontend.i18n import t
from frontend.utils import (
    FINAL_STATUSES,
    MAX_CONSECUTIVE_POLL_FAILURES,
    MAX_POLL_SECONDS,
    STAGES,
    _format_eta,
    _is_transient_http_error,
    _stage_index,
    api_get_report_with_retries,
    api_get_status,
)

_STAGE_KEY_TO_I18N: dict[str, str] = {
    "queued": "stage_queued",
    "planner": "stage_planner",
    "researcher": "stage_researcher",
    "sufficiency_check": "stage_sufficiency_check",
    "analyst": "stage_analyst",
    "writer": "stage_writer",
    "critic": "stage_critic",
    "finalize": "stage_finalize",
}


@st.fragment(run_every=2.0)
def poll_status_fragment() -> None:
    """Auto-polling fragment: runs every 2 seconds while task is active.

    Session-state keys consumed/modified:
        task_id, task_completed, polling_active, consecutive_failures,
        task_status, current_stage, last_status, last_error, report_data
    """
    task_id = st.session_state.get("task_id")
    if not task_id or st.session_state.get("task_completed"):
        return
    if not st.session_state.get("polling_active", True):
        if st.button(t("resume_polling"), key=f"resume_polling_{task_id}"):
            st.session_state.polling_active = True
            st.session_state.consecutive_failures = 0
            st.session_state.last_error = None
            st.rerun()
        return

    try:
        status = api_get_status(task_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            st.error(t("task_not_found"))
            st.session_state.polling_active = False
            st.session_state.last_error = t("task_not_found_404")
        elif _is_transient_http_error(exc):
            st.warning(t("backend_busy"))
            st.session_state.consecutive_failures += 1
        else:
            st.error(f"API error ({exc.response.status_code})")
            st.session_state.consecutive_failures += 1
        _check_excessive_failures()
        return
    except (httpx.TimeoutException, httpx.ConnectError):
        st.warning(t("connection_issue"))
        st.session_state.consecutive_failures += 1
        _check_excessive_failures()
        return
    except Exception as exc:
        st.session_state.last_error = str(exc)
        st.session_state.polling_active = False
        st.error(f"{t('unexpected_error')} {exc}")
        return

    st.session_state.last_status = status
    st.session_state.task_status = status.get("status")
    st.session_state.current_stage = status.get("current_stage")
    st.session_state.consecutive_failures = 0

    _render_status_ui(status)

    if status.get("status") in FINAL_STATUSES:
        st.session_state.task_completed = True
        st.session_state.polling_active = False

        if status["status"] == "FAILED":
            st.toast(t("research_failed_toast"), icon=":material/error:")
        else:
            st.toast(f"{t('research_completed_toast')}  :white_check_mark:")

        try:
            report = api_get_report_with_retries(task_id)
            st.session_state.report_data = report
        except Exception as exc:
            st.session_state.last_error = str(exc)

        st.rerun()


def _render_status_ui(status: dict[str, Any]) -> None:
    progress = float(status.get("progress") or 0.0)
    raw_stage = status.get("stage_label") or status.get("current_stage") or "Starting"
    stage_label = t(
        _STAGE_KEY_TO_I18N.get(status.get("current_stage", ""), raw_stage)
    )
    eta = status.get("estimated_remaining_seconds")
    issues = [str(i) for i in status.get("issues") or [] if str(i).strip()]

    status_container = st.status(
        label=f"**{stage_label}**",
        expanded=True,
        state="running",
    )

    with status_container:
        st.progress(progress, text=f"{t('overall')} {progress:.0%}")

        m1, m2, m3 = st.columns(3)
        m1.metric(t("status"), status.get("status", "UNKNOWN"))
        m2.metric(t("stage"), stage_label)
        m3.metric(t("eta"), _format_eta(eta, st.session_state.get("lang", "en")))

        st.divider()
        st.markdown(f"#### {t('pipeline_stages')}")
        current_idx = _stage_index(status.get("current_stage"))

        cols_per_row = 2
        for i, (stage_key, _stage_label_text) in enumerate(STAGES):
            row = i // cols_per_row
            col = i % cols_per_row
            if row * cols_per_row >= i - (i % cols_per_row) and col == 0:
                cols = st.columns(cols_per_row)
            target = cols[col]
            translated_label = t(_STAGE_KEY_TO_I18N.get(stage_key, stage_key))
            if i < current_idx:
                target.caption(f":white_check_mark: {translated_label}")
            elif i == current_idx:
                target.caption(
                    f":large_blue_circle: **{translated_label}** ({t('active')})"
                )
            else:
                target.caption(f":white_circle: {translated_label}")

        if issues:
            st.divider()
            with st.expander(f"{t('issues_label')} ({len(issues)})"):
                for issue in issues[:10]:
                    st.warning(issue, icon=":material/warning:")


def _check_excessive_failures() -> None:
    cf = st.session_state.get("consecutive_failures", 0)
    if cf >= MAX_CONSECUTIVE_POLL_FAILURES and st.session_state.get("polling_active"):
        st.session_state.polling_active = False
        st.warning(t("backend_unreachable"))
    elif cf > 0:
        elapsed = cf * 2  # approximate seconds
        if elapsed > MAX_POLL_SECONDS:
            st.session_state.polling_active = False
            st.warning(t("polling_timed_out"))
