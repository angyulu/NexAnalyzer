"""Session state for the QC Panel page.

Deliberately its own namespace, separate from `sample_report`: the two pages
read the same sample folder but hold different derived artifacts, and sharing
one dict would mean either page silently invalidating the other's results
whenever it re-ran.

A plain dict rather than a dataclass, matching `sample_report_state` — callers
mutate it in place and Streamlit persists the object. It has no migration
story, so read any key added later with `.get()`.
"""

import streamlit as st

_KEY = "qc_panel"


def initialize_qc_panel_state() -> None:
    """Create st.session_state["qc_panel"] if absent. Idempotent."""
    if _KEY not in st.session_state:
        st.session_state[_KEY] = {
            "folder": None,
            "scan": None,
            "magnification": None,
            "material": None,
            "reference_layer": "2L",
            "frames": None,             # list[contrast.FrameResult]
            "om_png": None,             # Image 1 bytes, clean (for the report)
            "om_diagnostic_png": None,  # Image 1 with the histogram row
            "raman_png": None,          # Image 2 bytes
            "raman_stats": None,
            "errors": None,             # list[(point, message)] from fitting
            # Fingerprints of the preset blocks each artifact was built from,
            # so editing one block need not throw away the other's figure.
            "optical_fingerprint": None,
            "raman_fingerprint": None,
        }


def get_qc_panel_state() -> dict:
    """Initialize (if needed) and return the QC Panel state dict."""
    initialize_qc_panel_state()
    return st.session_state[_KEY]


#: Derived keys, grouped by the preset block whose settings produced them.
_OPTICAL_ARTIFACTS = ("frames", "om_png", "om_diagnostic_png", "optical_fingerprint")
_RAMAN_ARTIFACTS = ("raman_png", "raman_stats", "errors", "raman_fingerprint")


def reset_results(state: dict) -> None:
    """Drop every derived artifact, keeping the operator's selections.

    Called whenever an input changes that invalidates *everything* -- the
    folder, the material, the layer. The Sample Report page learned this the
    hard way: leaving stale derived keys behind means a figure from the
    previous sample stays on screen next to the new sample's name.

    For a preset edit that touches only one technique, use
    `reset_optical_results` / `reset_raman_results` instead: a Raman peak edit
    must not discard a 30-second OM segmentation.
    """
    reset_optical_results(state)
    reset_raman_results(state)


def reset_optical_results(state: dict) -> None:
    """Drop the OM figures and the segmentation behind them."""
    for key in _OPTICAL_ARTIFACTS:
        state[key] = None


def reset_raman_results(state: dict) -> None:
    """Drop the Raman figure and its statistics."""
    for key in _RAMAN_ARTIFACTS:
        state[key] = None
