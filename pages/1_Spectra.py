"""
Spectra page: load Raman/PL files, run the material-preset auto-workflow,
inspect the fit, and export. The sidebar is this page's whole workflow
surface; the plot and fit-results table are the output.
"""

import streamlit as st

from core.version import APP_NAME, REPO_URL, __version__
from modules.spectra.ui.sidebar import render_sidebar
from modules.spectra.viz.live_plot import render_unified_plot, sync_pending_file_switch

st.title("📊 Raman & PL Spectra")
st.markdown("**Peak fitting with material presets — load a file, pick a material, run.**")

# Must run before the sidebar: applies a pending prev/next/select file
# switch and updates View Options' show_* state, both of which have to
# land before the sidebar's checkboxes are instantiated (see
# sync_pending_file_switch()'s docstring).
sync_pending_file_switch()

# Sidebar: material preset selection, Run Auto-Workflow, export, and
# view/reset controls — the sidebar is this page's single workflow surface.
with st.sidebar:
    render_sidebar()

render_unified_plot()  # Includes file navigation at top

st.markdown("---")
st.markdown(
    f"{APP_NAME} v{__version__} | "
    f"[User Guide]({REPO_URL}/blob/main/USER_GUIDE.md) | "
    f"[Report Issues]({REPO_URL}/issues)"
)
