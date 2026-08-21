"""
Isolated session-state namespace for the Sample Report page — deliberately
separate from st.session_state["files"]/["current_file"] (the Analysis
page's per-file model), since a sample folder's 18 spectra don't fit that
single-file-at-a-time shape.
"""

import streamlit as st

_KEY = "sample_report"


def initialize_sample_report_state() -> None:
    """Create st.session_state["sample_report"] if absent. Idempotent."""
    if _KEY not in st.session_state:
        st.session_state[_KEY] = {
            "folder": None,
            "scan": None,
            "magnification": None,
            "material": None,
            "batch_result": None,
            "raman_stats": None,
            "pl_stats": None,
            "pptx_bytes": None,
            "slide_images": None,
        }


def get_sample_report_state() -> dict:
    """Initialize (if needed) and return the Sample Report state dict."""
    initialize_sample_report_state()
    return st.session_state[_KEY]
