"""
NexAnalyzer: Nexstrom's measurement data analyzer.

Streamlit entry point and composition root. This file does global setup
(page config, module session state) and page routing only — analysis code
lives in modules/<technique>/, platform code in core/, and page content in
pages/.

Adding a technique module: drop it under modules/, initialize its session
state here, and register its pages below.

The navigation carries one named section, "Process", and leaves the rest
unlabelled. It used to carry a group called "Raman & PL", which stopped being
true at v4.0.0 when the QC Panel grew an OM image and Material Presets grew an
optical block; the lesson recorded then was that a *technique* label goes stale
as techniques are added, and that with few pages no such label outperforms the
page names.

"Process" survives that argument because it names a **data source**, not a
technique: Datalog and Runcard read the deposition tool's own logs and recipes,
where the other three read measurements taken afterwards. That split is a fact
about where the files come from, so no future technique can falsify it. The
remaining three stay unlabelled rather than take a counterpart heading — they
are simply "everything else", and naming that adds nothing.
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
qc_report_page = st.Page("pages/2_QC_Report.py", title="QC Report", icon="🔬")
material_presets_page = st.Page("pages/3_Material_Presets.py", title="Material Presets", icon="🧪")
datalog_page = st.Page("pages/4_Datalog.py", title="Datalog", icon="📈")
runcard_page = st.Page("pages/5_Runcard.py", title="Runcard", icon="📋")

nav = st.navigation(
    {
        "": [
            spectra_page,
            qc_report_page,
            material_presets_page,
        ],
        "Process": [
            datalog_page,
            runcard_page,
        ],
    },
    position="sidebar",
)

st.sidebar.caption(f"{APP_NAME} v{__version__} — {APP_TAGLINE}")

nav.run()
