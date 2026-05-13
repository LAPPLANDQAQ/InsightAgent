"""Coverage visualization with Plotly radar chart and metric cards."""

from typing import Any

import streamlit as st

from frontend.i18n import t
from frontend.utils import _coverage_items

_PLOTLY_AVAILABLE = True
try:
    import plotly.graph_objects as go
except ImportError:
    _PLOTLY_AVAILABLE = False


def render_coverage_tab(quality_metrics: dict[str, Any]) -> None:
    """Render Coverage tab: Plotly radar chart (or SVG fallback) + metric cards."""
    coverage = _coverage_items(quality_metrics)
    if not coverage:
        st.info(t("no_coverage_metrics"))
        return

    score = float(quality_metrics.get("score") or 0.0)
    missing = quality_metrics.get("missing_dimensions") or []
    total_evidence = sum(item["evidence_count"] for item in coverage)
    sufficient_count = sum(1 for item in coverage if item["sufficient"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("coverage_score"), f"{score:.0%}")
    c2.metric(
        t("sufficient_dimensions"), f"{sufficient_count}/{len(coverage)}"
    )
    c3.metric(t("total_evidence"), str(total_evidence))
    c4.metric(t("missing_dimensions"), str(len(missing)))

    if _PLOTLY_AVAILABLE:
        _render_plotly_radar(coverage, total_evidence)
    else:
        import streamlit.components.v1 as components

        from frontend.utils import _radar_svg

        components.html(
            _radar_svg(coverage, st.session_state.get("lang", "en")),
            height=620,
            scrolling=True,
        )

    _render_dimension_table(coverage)


def _render_plotly_radar(
    coverage: list[dict[str, Any]], total_evidence: int
) -> None:
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=[item["evidence_count"] for item in coverage],
            theta=[item["dimension"] for item in coverage],
            fill="toself",
            name=t("chart_evidence"),
            line={"color": "#6C63FF", "width": 2},
            fillcolor="rgba(108, 99, 255, 0.2)",
            hovertemplate="<b>%{theta}</b><br>Evidence: %{r}<extra></extra>",
        )
    )

    avg = total_evidence / len(coverage) if coverage else 0
    fig.add_trace(
        go.Scatterpolar(
            r=[avg] * len(coverage),
            theta=[item["dimension"] for item in coverage],
            mode="lines",
            name=t("chart_average"),
            line={"color": "#F59E0B", "width": 1, "dash": "dot"},
        )
    )

    fig.update_layout(
        polar={
            "radialaxis": {
                "visible": True,
                "showline": False,
                "gridcolor": "rgba(255,255,255,0.1)",
            },
            "angularaxis": {
                "gridcolor": "rgba(255,255,255,0.1)",
                "linewidth": 0,
            },
            "bgcolor": "rgba(0,0,0,0)",
        },
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FAFAFA"},
        margin={"l": 60, "r": 60, "t": 20, "b": 20},
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.15,
            "xanchor": "center",
            "x": 0.5,
            "font": {"color": "#9DA3B4"},
        },
        height=420,
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_dimension_table(coverage: list[dict[str, Any]]) -> None:
    import pandas as pd

    with st.expander(t("dimension_details"), expanded=False):
        df = pd.DataFrame(
            [
                {
                    t("col_dimension"): item["dimension"],
                    t("col_evidence_count"): item["evidence_count"],
                    t("col_status"): (
                        f":white_check_mark: {t('sufficient')}"
                        if item["sufficient"]
                        else f":warning: {t('needs_improvement')}"
                    ),
                }
                for item in coverage
            ]
        )
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )
