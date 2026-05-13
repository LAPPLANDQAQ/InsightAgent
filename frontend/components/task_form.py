"""Task creation form with inline validation."""

from collections.abc import Mapping

import streamlit as st

from frontend.i18n import t
from frontend.utils import _split_csv


def is_active_task_running(state: Mapping[str, object] | None = None) -> bool:
    """Return whether the session has a non-terminal active task."""
    current = st.session_state if state is None else state
    return bool(current.get("task_id")) and not bool(current.get("task_completed"))


def should_disable_form(state: Mapping[str, object] | None = None) -> bool:
    """Return whether task inputs and submit should be disabled."""
    current = st.session_state if state is None else state
    return bool(current.get("form_disabled")) or is_active_task_running(current)


def render_task_form() -> dict | None:
    """Render the analysis request form. Returns submitted data dict or None.

    Session-state keys consumed:
        form_disabled (bool), task_id (str | None)
    """
    with st.container(border=True):
        st.markdown(f"### {t('new_analysis')}")
        st.caption(t("new_analysis_desc"))

        disabled = should_disable_form()
        api_call_in_progress = bool(st.session_state.get("form_disabled"))

        query = st.text_input(
            label=t("form_query_label"),
            placeholder=t("form_query_placeholder"),
            help=t("form_query_help"),
            disabled=disabled,
            key="form_query",
        )

        competitors = st.text_input(
            label=t("form_competitors_label"),
            placeholder=t("form_competitors_placeholder"),
            help=t("form_competitors_help"),
            disabled=disabled,
            key="form_competitors",
        )

        dimensions = st.text_input(
            label=t("form_dimensions_label"),
            placeholder=t("form_dimensions_placeholder"),
            help=t("form_dimensions_help"),
            disabled=disabled,
            key="form_dimensions",
        )

        can_submit = bool(query and len(query.strip()) >= 2)
        if query and len(query.strip()) < 2:
            st.caption(t("query_too_short"))

        col1, col2, col_space = st.columns([1, 1, 2])
        with col1:
            submitted = st.button(
                t("start_research"),
                type="primary",
                use_container_width=True,
                disabled=not can_submit or disabled,
            )
        with col2:
            if st.session_state.get("task_id"):
                if st.button(
                    t("new_task"),
                    use_container_width=True,
                    disabled=api_call_in_progress,
                ):
                    from frontend.utils import clear_task_state

                    clear_task_state()
                    st.rerun()

        if submitted and can_submit:
            return {
                "query": query.strip(),
                "competitors": _split_csv(competitors),
                "dimensions": _split_csv(dimensions),
            }
    return None
