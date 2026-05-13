"""Task creation form with inline validation."""

import streamlit as st

from frontend.i18n import t
from frontend.utils import _split_csv


def render_task_form() -> dict | None:
    """Render the analysis request form. Returns submitted data dict or None.

    Session-state keys consumed:
        form_disabled (bool), task_id (str | None)
    """
    with st.container(border=True):
        st.markdown(f"### {t('new_analysis')}")
        st.caption(t("new_analysis_desc"))

        disabled = bool(st.session_state.get("form_disabled"))

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
                    disabled=disabled,
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
