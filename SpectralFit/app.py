"""
SpectralFit: Raman & Photoluminescence Spectrum Analysis Tool

Main Streamlit application entry point.
v2.2: Single-page, three-panel layout with unified workflow.
"""

import streamlit as st
from src.ui.sidebar import render_sidebar
from src.ui.file_panel import render_file_panel
from src.ui.control_panel import render_control_panel
from src.visualization.unified_plot import render_unified_plot
from src.ui.session_state import initialize_session_state

# Configure page
st.set_page_config(
    page_title="SpectralFit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",  # v2.2: Sidebar now minimal (file upload only)
)

# Initialize session state
initialize_session_state()

# Add mobile detection flag initialization
if 'is_mobile' not in st.session_state:
    st.session_state['is_mobile'] = False

# Add expanded_section initialization
if 'expanded_section' not in st.session_state:
    st.session_state['expanded_section'] = 'processing_range'

# Mobile detection script (Phase 1.2.1)
# Inject JavaScript to detect viewport width and set is_mobile flag
st.markdown(
    """
    <script>
    function checkMobile() {
        const isMobile = window.innerWidth < 1024;
        // Note: Streamlit doesn't support direct JS->Python callbacks
        // This is a placeholder for viewport detection
        // In production, consider using st.experimental_get_query_params() workaround
    }
    checkMobile();
    window.addEventListener('resize', checkMobile);
    </script>
    """,
    unsafe_allow_html=True
)

# Title
st.title("📊 SpectralFit v2.2")
st.markdown("**Raman & Photoluminescence Spectrum Analysis Tool**")

# Sidebar (minimal - just file upload for v2.2)
with st.sidebar:
    render_sidebar()

# v2.2: Three-panel layout (desktop) or stacked layout (mobile)
is_mobile = st.session_state.get('is_mobile', False)

if is_mobile:
    # Mobile: Vertical stack (Controls → Plot)
    # **FIX (Issue 6d)**: File panel removed - navigation now in plot
    render_control_panel()
    st.markdown("---")
    render_unified_plot()
else:
    # Desktop: Two columns (70% plot / 30% controls)
    # **FIX (Issue 6d)**: Removed left file panel - navigation now at top of plot
    col_center, col_right = st.columns([3.5, 1.5])

    with col_center:
        render_unified_plot()  # Now includes file navigation at top

    with col_right:
        render_control_panel()

# Footer
st.markdown("---")
st.markdown(
    "SpectralFit v2.2 | "
    "[Documentation](../specs/001-spectralfit/quickstart.md) | "
    "[Report Issues](https://github.com/your-repo/issues)"
)
