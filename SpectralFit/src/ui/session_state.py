"""
Session state management utilities for Streamlit.

This module provides functions to:
- Initialize session state on first load
- Access and update session state safely
- Manage multiple spectrum files
"""

import streamlit as st
from pathlib import Path
from ..models.project import StylingPreferences


def get_default_preset_path() -> str:
    """
    Get the default path to material_presets.xlsx.

    Returns absolute path to ensure it works regardless of working directory.
    """
    # Get the directory where this file is located
    this_file = Path(__file__).resolve()
    # Navigate to SpectralFit root: src/ui -> src -> SpectralFit
    spectralfit_root = this_file.parent.parent.parent
    # Build path to presets folder
    preset_path = spectralfit_root / "presets" / "material_presets.xlsx"
    return str(preset_path)


def initialize_session_state():
    """
    Initialize session state on first app load.

    Creates the following keys in st.session_state:
    - mode: str ("Raman" or "PL")
    - files: dict (filename -> SpectrumFile mapping)
    - current_file: Optional[str] (selected filename)
    - global_styling: StylingPreferences
    - plot_width_preset: str (v2.1+, FR-14: "Compact" | "Standard" | "Wide" | "Full")
    - preset_library: PresetLibrary or None (v2.3: loaded material presets)
    - selected_preset: MaterialPreset or None (v2.3: currently selected preset)
    - preset_file_path: str (v2.3: path to material_presets.xlsx)
    - auto_workflow_trigger: DEPRECATED (v2.3+: removed, workflow executes directly on button click)

    This function is idempotent (safe to call multiple times).
    """
    if "mode" not in st.session_state:
        st.session_state["mode"] = "Raman"

    if "files" not in st.session_state:
        st.session_state["files"] = {}

    if "current_file" not in st.session_state:
        st.session_state["current_file"] = None

    if "global_styling" not in st.session_state:
        st.session_state["global_styling"] = StylingPreferences()

    # v2.1+ (FR-14): Plot width control
    if "plot_width_preset" not in st.session_state:
        st.session_state["plot_width_preset"] = "Standard"  # Default: 75% width

    # v2.3: Material preset system
    if "preset_library" not in st.session_state:
        st.session_state["preset_library"] = None
    if "selected_preset" not in st.session_state:
        st.session_state["selected_preset"] = None
    if "preset_file_path" not in st.session_state:
        st.session_state["preset_file_path"] = get_default_preset_path()
    # DEPRECATED: auto_workflow_trigger no longer needed (workflow executes directly)


def get_current_spectrum():
    """
    Get the currently selected SpectrumFile.

    Returns
    -------
    SpectrumFile or None
        Current spectrum if one is selected, else None.

    Examples
    --------
    >>> spectrum = get_current_spectrum()
    >>> if spectrum:
    ...     print(f"Loaded: {spectrum.filename}")
    """
    current_file = st.session_state.get("current_file")
    if current_file is None:
        return None

    files = st.session_state.get("files", {})
    return files.get(current_file)


def add_spectrum_file(spectrum_file):
    """
    Add a SpectrumFile to session state.

    Parameters
    ----------
    spectrum_file : SpectrumFile
        Spectrum file to add.

    Notes
    -----
    If a file with the same filename exists, it will be overwritten.
    The added file automatically becomes the current selection.
    """
    if "files" not in st.session_state:
        st.session_state["files"] = {}

    st.session_state["files"][spectrum_file.filename] = spectrum_file
    st.session_state["current_file"] = spectrum_file.filename


def remove_spectrum_file(filename: str):
    """
    Remove a SpectrumFile from session state.

    Parameters
    ----------
    filename : str
        Filename to remove.

    Notes
    -----
    If the removed file was the current selection, current_file is set to None
    (or to the first remaining file if any exist).
    """
    if filename not in st.session_state.get("files", {}):
        return

    del st.session_state["files"][filename]

    # Update current_file if the removed file was selected
    if st.session_state.get("current_file") == filename:
        remaining_files = list(st.session_state["files"].keys())
        st.session_state["current_file"] = remaining_files[0] if remaining_files else None


def clear_all_files():
    """
    Remove all SpectrumFile objects from session state.

    This is useful for "New Project" functionality.
    """
    st.session_state["files"] = {}
    st.session_state["current_file"] = None


def get_mode() -> str:
    """
    Get current spectroscopy mode.

    Returns
    -------
    str
        "Raman" or "PL"
    """
    return st.session_state.get("mode", "Raman")


def set_mode(mode: str):
    """
    Set spectroscopy mode.

    Parameters
    ----------
    mode : str
        "Raman" or "PL"

    Raises
    ------
    ValueError
        If mode is not "Raman" or "PL"
    """
    if mode not in ["Raman", "PL"]:
        raise ValueError(f"mode must be 'Raman' or 'PL' (got {mode})")

    st.session_state["mode"] = mode


def get_styling() -> StylingPreferences:
    """
    Get global styling preferences.

    Returns
    -------
    StylingPreferences
        Current styling settings.
    """
    if "global_styling" not in st.session_state:
        st.session_state["global_styling"] = StylingPreferences()

    return st.session_state["global_styling"]


def update_styling(styling: StylingPreferences):
    """
    Update global styling preferences.

    Parameters
    ----------
    styling : StylingPreferences
        New styling settings.
    """
    st.session_state["global_styling"] = styling
