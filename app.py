"""
NexAnalyzer: Nexstrom's measurement data analyzer.

Streamlit entry point and composition root. This file does global setup
(page config, module session state) and page routing only — analysis code
lives in modules/<technique>/, platform code in core/, and page content in
pages/.

Adding a technique module: drop it under modules/, initialize its session
state here, and register its pages below.
"""

import streamlit as st

from core.version import APP_NAME, APP_TAGLINE, __version__
from modules.spectra.ui.session_state import initialize_session_state

# Configure page (must run once, before any other Streamlit command)
st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
    # Expanded by default — the sidebar (file upload, material preset,
    # Run Auto-Workflow) is the only way to process a spectrum.
    initial_sidebar_state="expanded",
)

# Initialize each module's session state (shared across all its pages)
initialize_session_state()

spectra_page = st.Page("pages/1_Spectra.py", title="Spectra", icon="📊", default=True)
sample_report_page = st.Page("pages/2_Sample_Report.py", title="Sample Report", icon="🖼️")
material_presets_page = st.Page("pages/3_Material_Presets.py", title="Material Presets", icon="🧪")

nav = st.navigation(
    {"Raman & PL": [spectra_page, sample_report_page, material_presets_page]},
    position="sidebar",
)

st.sidebar.caption(f"{APP_NAME} v{__version__} — {APP_TAGLINE}")

nav.run()
