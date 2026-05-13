"""Custom CSS for InsightAgent dark-themed dashboard."""

import streamlit as st

PRIMARY = "#6C63FF"
PRIMARY_LIGHT = "#8B83FF"
BG_DARK = "#0E1117"
BG_CARD = "#1E2130"
BG_SIDEBAR = "#161922"
TEXT_PRIMARY = "#FAFAFA"
TEXT_SECONDARY = "#9DA3B4"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
ERROR = "#EF4444"
BORDER = "#2A2D3A"

CSS = """
<style>
/* Brand header */
.brand-header {
  padding: 0.25rem 0 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-bottom: 1px solid #2A2D3A;
  margin-bottom: 1rem;
}
.brand-icon { font-size: 1.6rem; }
.brand-title { font-size: 1.4rem; font-weight: 700; color: #FAFAFA; }
.brand-subtitle {
  font-size: 0.8rem; color: #9DA3B4; margin-left: 0.25rem;
}

/* Health badge */
.health-badge {
  font-size: 0.75rem; padding: 0.15rem 0.6rem;
  border-radius: 1rem; background: #1E2130; border: 1px solid #2A2D3A;
}

/* Card border containers */
section[data-testid="stContainer"] {
  background: #1E2130; border: 1px solid #2A2D3A;
  border-radius: 10px; padding: 1.25rem;
}

/* Sidebar */
section[data-testid="stSidebar"] { background: #161922; }
section[data-testid="stSidebar"] section[data-testid="stContainer"] {
  background: #1E2130; border-radius: 8px; padding: 0.6rem 0.8rem;
  margin-bottom: 0.4rem;
}

/* Metric cards */
div[data-testid="stMetric"] {
  background: #1E2130; border: 1px solid #2A2D3A;
  border-radius: 8px; padding: 0.5rem 0.75rem;
}
div[data-testid="stMetric"] label { color: #9DA3B4; font-size: 0.75rem; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
  color: #FAFAFA; font-weight: 700; font-size: 1.5rem;
}

/* Progress bar */
div[data-testid="stProgress"] > div { background: #2A2D3A; }
div[data-testid="stProgress"] > div > div { background: #6C63FF; }

/* Tabs */
button[data-baseweb="tab"] { color: #9DA3B4; font-size: 0.85rem; }
button[data-baseweb="tab"][aria-selected="true"] { color: #6C63FF; }
div[data-baseweb="tab-highlight"] { background: #6C63FF; }

/* Primary button */
button[kind="primary"] { background: #6C63FF; border: none; }
button[kind="primary"]:hover { background: #8B83FF; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0E1117; }
::-webkit-scrollbar-thumb { background: #2A2D3A; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3A3D4A; }

/* Expander */
div[data-testid="stExpander"] {
  background: #1E2130; border: 1px solid #2A2D3A; border-radius: 8px;
}

/* Warning / Error / Info boxes */
div[data-testid="stAlert"] {
  border-radius: 8px;
}

/* Toast */
div[data-testid="stToast"] {
  background: #1E2130; border: 1px solid #2A2D3A; border-radius: 8px;
}

/* Data editor / dataframe */
div[data-testid="stDataEditor"] { border-radius: 8px; }
div[data-testid="stTable"] { border-radius: 8px; }
</style>
"""


def inject_custom_css() -> None:
    """Inject the InsightAgent dark-theme CSS into the Streamlit page."""
    st.markdown(CSS, unsafe_allow_html=True)
