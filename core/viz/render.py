"""
Streamlit rendering of Plotly figures at the user's chosen page width.

Technique-agnostic: any module's figure goes through here so the
plot_width_preset setting applies uniformly across the app.
"""

from typing import Optional

import plotly.graph_objects as go

# Fraction of the page each width preset occupies.
_WIDTH_MAP = {
    "Compact": 0.60,
    "Standard": 0.75,
    "Wide": 0.90,
    "Full": 1.0,
}


def render_plot(fig: go.Figure, key: Optional[str] = None) -> None:
    """Render a Plotly figure respecting the plot_width_preset session setting.

    Wraps the chart in a proportionally-sized ``st.columns`` container so the
    Streamlit ``use_container_width=True`` flag fills the correct fraction of
    the page rather than the full width.
    """
    import streamlit as st

    preset = st.session_state.get("plot_width_preset", "Full")
    frac = _WIDTH_MAP.get(preset, 1.0)

    if frac >= 1.0:
        st.plotly_chart(fig, use_container_width=True, key=key)
    else:
        col_plot, _ = st.columns([frac, 1.0 - frac])
        with col_plot:
            st.plotly_chart(fig, use_container_width=True, key=key)
