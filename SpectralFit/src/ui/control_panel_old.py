"""
Right panel UI component for processing controls in accordion sections.

This module provides the control panel rendering for the single-page layout:
- Accordion sections (st.expander) for each processing stage
- Sequential workflow with auto-expand
- Integration of processing controls from original tab modules
"""

import streamlit as st
from typing import Optional
from .session_state import get_current_spectrum


def is_section_enabled(section_id: str, spectrum: Optional[object]) -> bool:
    """
    Check if a processing section is enabled based on workflow dependencies.

    Parameters
    ----------
    section_id : str
        Section identifier: "processing_range", "despike", "baseline", "peak_fit", "export".
    spectrum : SpectrumFile or None
        Current spectrum file.

    Returns
    -------
    bool
        True if section is enabled and can be expanded.
    """
    if spectrum is None:
        return section_id in ["processing_range", "despike", "baseline", "export"]

    # Peak Fit requires baseline to be done
    if section_id == "peak_fit":
        baseline_done = getattr(spectrum, 'baseline_done', False)
        return baseline_done

    # All other sections always enabled
    return True


def render_view_options():
    """
    Render plot layer visibility checkboxes (View Options subsection).

    This will be fully implemented in Phase 2.2.
    """
    with st.expander("🔍 View Options", expanded=False):
        st.markdown("**Plot Layer Visibility**")

        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Show Raw", value=True, key="show_raw")
            st.checkbox("Show De-spiked", value=False, key="show_despiked")
            st.checkbox("Show Baseline-corrected", value=False, key="show_corrected")
        with col2:
            st.checkbox("Show Fit", value=False, key="show_fit")
            st.checkbox("Show Components", value=False, key="show_components")

        st.caption("Toggle plot layers on/off without reprocessing.")


def render_processing_range_section(is_expanded: bool):
    """Render Processing Range section (placeholder for Phase 3.4.1)."""
    with st.expander("1️⃣ Processing Range", expanded=is_expanded):
        st.info("Processing Range controls will be migrated here in Phase 3.4.1")
        # Placeholder for X-range controls


def render_despike_section(is_expanded: bool):
    """Render De-spiking section (placeholder for Phase 3.4.2)."""
    with st.expander("2️⃣ De-spiking", expanded=is_expanded):
        st.info("De-spiking controls will be migrated here in Phase 3.4.2")
        # Placeholder for despike threshold slider


def render_baseline_section(is_expanded: bool):
    """Render Baseline Correction section (placeholder for Phase 3.4.3)."""
    with st.expander("3️⃣ Baseline Correction", expanded=is_expanded):
        st.info("Baseline Correction controls will be migrated here in Phase 3.4.3")
        # Placeholder for baseline algorithm, degree, lambda, p controls


def render_peak_fit_section(is_expanded: bool, is_enabled: bool):
    """Render Peak Fitting section (placeholder for Phase 3.4.4)."""
    if not is_enabled:
        with st.expander("4️⃣ Peak Fitting", expanded=False):
            st.warning("⚠️ Complete baseline correction first")
            return

    with st.expander("4️⃣ Peak Fitting", expanded=is_expanded):
        st.info("Peak Fitting controls will be migrated here in Phase 3.4.4")
        # Placeholder for peak table and fit controls


def render_export_section(is_expanded: bool):
    """Render Export section (placeholder for Phase 3.4.5)."""
    with st.expander("5️⃣ Export", expanded=is_expanded):
        st.info("Export controls will be migrated here in Phase 3.4.5")
        # Placeholder for export dialog


def render_control_panel():
    """
    Render the right panel with accordion sections for all processing controls.

    This function should be called from app.py within the right column.
    """
    # Get current file and expanded section state
    spectrum = get_current_spectrum()
    expanded_section = st.session_state.get('expanded_section', 'processing_range')

    # Mobile: Add "Jump to Plot" link (will be fully implemented in Phase 4.3.3)
    is_mobile = st.session_state.get('is_mobile', False)
    if is_mobile:
        st.markdown("📊 [Jump to Plot](#plot-anchor)")

    # View Options (always at top)
    render_view_options()

    st.markdown("---")
    st.markdown("### Processing Workflow")

    # Render accordion sections in order
    render_processing_range_section(is_expanded=(expanded_section == 'processing_range'))
    render_despike_section(is_expanded=(expanded_section == 'despike'))
    render_baseline_section(is_expanded=(expanded_section == 'baseline'))

    peak_fit_enabled = is_section_enabled('peak_fit', spectrum)
    render_peak_fit_section(
        is_expanded=(expanded_section == 'peak_fit'),
        is_enabled=peak_fit_enabled
    )

    render_export_section(is_expanded=(expanded_section == 'export'))
