"""Session state for the Plot Explorer page.

Its own namespace, following `modules.optical.ui.qc_panel_state`: this page
shares nothing with the spectra workflow -- no material preset, no sample
folder, no fitted peaks -- and putting its keys in the global session state
would mean two unrelated features able to invalidate each other.

A plain dict rather than a dataclass, matching the other state modules:
callers mutate it in place and Streamlit persists the object. It has no
migration story, so read any key added later with ``.get()``.
"""

import streamlit as st

from ..viz.scatter import DEFAULT_CONFIG

_KEY = "plot_explorer"


def initialize_state() -> None:
    """Create st.session_state["plot_explorer"] if absent. Idempotent."""
    if _KEY not in st.session_state:
        st.session_state[_KEY] = {
            # The operator's choices.
            "path": None,          # workbook path from the native dialog
            "sheet": None,         # the one sheet being plotted
            "header_rows": 1,
            "coercions": {},       # column name -> strategy
            "filters": [],         # list of RowFilter-shaped dicts
            "config": dict(DEFAULT_CONFIG),
            # Derived, and dropped whenever the file or sheet changes.
            "sheets": None,        # list[SheetInfo] for the picker
            "load_error": None,
        }


def get_state() -> dict:
    """Initialize (if needed) and return the Plot Explorer state dict."""
    initialize_state()
    return st.session_state[_KEY]


def reset_sheet_selections(state: dict) -> None:
    """Forget everything that described the *previous* sheet's columns.

    Coercions, filters and the plot config all name columns, and the sheets in
    one workbook share almost no column names -- carrying them across a sheet
    switch is how a plot comes to claim an axis the new sheet has never had.
    The workbook path and the sheet list survive.
    """
    state["coercions"] = {}
    state["filters"] = []
    state["config"] = dict(DEFAULT_CONFIG)
    state["load_error"] = None


def reset_workbook(state: dict) -> None:
    """Forget the open workbook entirely, selections included."""
    state["sheet"] = None
    state["sheets"] = None
    reset_sheet_selections(state)
