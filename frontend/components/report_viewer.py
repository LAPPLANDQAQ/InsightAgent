"""Report viewer with tabbed layout for completed task results."""

from typing import Any

import streamlit as st

from frontend.components.coverage_charts import render_coverage_tab
from frontend.i18n import t
from frontend.utils import _document_filename


def render_report_view(report: dict[str, Any]) -> None:
    """Render completed report with Report / Coverage / Quality Data / Evidence tabs.

    Session-state key consumed:
        report_data (dict)
    """
    task_id = str(report.get("task_id") or "task")
    markdown = str(report.get("report_markdown") or "")
    quality_metrics = dict(report.get("quality_metrics") or {})

    banner_col1, banner_col2 = st.columns([5, 1])
    with banner_col1:
        st.success(t("research_completed"), icon=":material/check_circle:")
    with banner_col2:
        st.download_button(
            label=t("download_markdown"),
            data=markdown.encode("utf-8"),
            file_name=_document_filename(task_id),
            mime="text/markdown",
            use_container_width=True,
        )

    tabs = st.tabs(
        [
            t("tab_report"),
            t("tab_coverage"),
            t("tab_quality_data"),
            t("tab_evidence"),
        ]
    )

    # --- Report tab ---
    with tabs[0]:
        st.markdown(markdown or t("no_report_content"))

    # --- Coverage tab ---
    with tabs[1]:
        render_coverage_tab(quality_metrics)

    # --- Quality Data tab ---
    with tabs[2]:
        from frontend.components.evidence_viewer import citation_summary

        summary = citation_summary(
            markdown, quality_metrics.get("evidences") or []
        )

        q1, q2, q3 = st.columns(3)
        q1.metric(t("total_citations"), summary.get("citation_count", 0))
        density_pct = f"{summary.get('citation_density', 0) * 100:.2f}%"
        q2.metric(t("citation_density"), density_pct)
        q3.metric(
            t("missing_references"), str(len(summary.get("missing_refs", [])))
        )

        if summary.get("missing_refs"):
            st.warning(
                f"{t('missing_evidence_refs')} {', '.join(summary['missing_refs'])}"
            )

        with st.expander(t("raw_quality_metrics")):
            st.json(quality_metrics)

    # --- Evidence tab ---
    with tabs[3]:
        from frontend.components.evidence_viewer import build_evidence_lookup

        evidences = quality_metrics.get("evidences") or []
        lookup = build_evidence_lookup(evidences)

        if lookup:
            import pandas as pd

            rows = [
                {
                    t("col_evidence_id"): str(ev_id),
                    t("col_source"): str(
                        ev_data.get("source_url", "")
                        or ev_data.get("source", "")
                        or ""
                    )[:80],
                    t("col_relevance"): str(ev_data.get("relevance", "")),
                }
                for ev_id, ev_data in lookup.items()
            ]
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(t("no_evidence_records"))
