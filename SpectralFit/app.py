"""
SpectralFit: Raman & Photoluminescence Spectrum Analysis Tool

Main Streamlit application entry point.
"""

import streamlit as st
from src.ui.sidebar import render_sidebar
from src.ui.preprocess_tab import render_preprocess_tab
from src.ui.fit_tab import render_fit_tab
from src.ui.export_tab import render_export_tab
from src.ui.session_state import initialize_session_state

# Configure page
st.set_page_config(
    page_title="SpectralFit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
initialize_session_state()

# Title
st.title("📊 SpectralFit")
st.markdown("**Raman & Photoluminescence Spectrum Analysis Tool**")

# Sidebar
with st.sidebar:
    render_sidebar()

# Main tabs
tab1, tab2, tab3 = st.tabs(["1. Pre-process", "2. Fit Peaks", "3. Export"])

with tab1:
    render_preprocess_tab()

with tab2:
    render_fit_tab()

with tab3:
    render_export_tab()

# Footer
st.markdown("---")
st.markdown(
    "SpectralFit v1.0.0 | "
    "[Documentation](../specs/001-spectralfit/quickstart.md) | "
    "[Report Issues](https://github.com/your-repo/issues)"
)
