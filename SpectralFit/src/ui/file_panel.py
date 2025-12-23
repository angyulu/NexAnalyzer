"""
Left panel UI component for file list and status badges.

This module provides the file panel rendering for the single-page layout:
- File cards with mode chips
- Status badges (Despike, Baseline, Fit)
- Clickable navigation to processing sections
"""

import streamlit as st
from typing import Optional
from ..models.spectrum import SpectrumFile
from .session_state import get_current_spectrum


def compute_badge_state(spectrum: Optional[SpectrumFile], stage: str) -> str:
    """
    Compute badge state for a processing stage.

    Parameters
    ----------
    spectrum : SpectrumFile or None
        Spectrum file to check status for.
    stage : str
        Processing stage: "despike", "baseline", or "fit".

    Returns
    -------
    str
        Badge state: "not_run", "done", or "warning".
    """
    if spectrum is None:
        return "not_run"

    # Get status flags (will be added in Phase 3.1)
    despike_done = getattr(spectrum, 'despike_done', False)
    baseline_done = getattr(spectrum, 'baseline_done', False)
    fit_done = getattr(spectrum, 'fit_done', False)
    fit_stale = getattr(spectrum, 'fit_stale', False)

    if stage == "despike":
        return "done" if despike_done else "not_run"
    elif stage == "baseline":
        return "done" if baseline_done else "not_run"
    elif stage == "fit":
        if fit_stale:
            return "warning"
        return "done" if fit_done else "not_run"
    else:
        return "not_run"


def render_status_badge(badge_type: str, state: str, filename: str):
    """
    Render a status badge button.

    Parameters
    ----------
    badge_type : str
        Badge label: "Despike", "Baseline", or "Fit".
    state : str
        Badge state: "not_run", "done", or "warning".
    filename : str
        Filename for unique button key.
    """
    # Badge styling based on state
    if state == "done":
        emoji = "✅"
        color = "green"
    elif state == "warning":
        emoji = "⚠️"
        color = "orange"
    else:
        emoji = "⚪"
        color = "gray"

    # Create clickable badge button
    badge_key = f"badge_{badge_type.lower()}_{filename}"
    if st.button(f"{emoji} {badge_type}", key=badge_key, help=f"Jump to {badge_type} section"):
        # Navigate to section (will be implemented in Phase 3.3)
        st.session_state['expanded_section'] = badge_type.lower()
        st.session_state['scroll_target'] = badge_type.lower()
        st.rerun()


def render_file_card(filename: str, spectrum: SpectrumFile, is_current: bool):
    """
    Render a file card with status badges.

    Parameters
    ----------
    filename : str
        Filename to display.
    spectrum : SpectrumFile
        Spectrum file data.
    is_current : bool
        Whether this is the currently selected file.
    """
    # Card container with border styling
    card_style = "border: 2px solid #4CAF50;" if is_current else "border: 1px solid #ddd;"

    with st.container():
        st.markdown(f'<div style="{card_style} padding: 10px; border-radius: 5px; margin-bottom: 10px;">',
                    unsafe_allow_html=True)

        # Filename with click to select
        if st.button(filename, key=f"select_{filename}", use_container_width=True):
            st.session_state['current_file'] = filename
            st.rerun()

        # **FIX (Issue 6d)**: Hide mode chip and status badges per user request
        # # Mode chip
        # mode_color = "#2196F3" if spectrum.mode == "Raman" else "#FF9800"
        # st.markdown(
        #     f'<span style="background-color: {mode_color}; color: white; '
        #     f'padding: 2px 8px; border-radius: 3px; font-size: 12px;">{spectrum.mode}</span>',
        #     unsafe_allow_html=True
        # )

        # # Status badges row
        # col1, col2, col3 = st.columns(3)
        # with col1:
        #     render_status_badge("Despike", compute_badge_state(spectrum, "despike"), filename)
        # with col2:
        #     render_status_badge("Baseline", compute_badge_state(spectrum, "baseline"), filename)
        # with col3:
        #     render_status_badge("Fit", compute_badge_state(spectrum, "fit"), filename)

        st.markdown('</div>', unsafe_allow_html=True)


def render_file_panel():
    """
    Render the left panel with file list and status badges.

    This function should be called from app.py within the left column.
    """
    st.header("Files")

    # Get files from session state
    files = st.session_state.get("files", {})
    current_file = st.session_state.get("current_file")

    if not files:
        st.info("No files loaded. Upload files to begin analysis.")
        return

    # Render file cards
    for filename, spectrum in files.items():
        is_current = (filename == current_file)
        render_file_card(filename, spectrum, is_current)
