"""
Project state persistence (JSON save/load).

This module provides functions to:
- Save complete session state to JSON
- Load project from JSON and restore session state
- Validate project schema version compatibility
"""

import json
from datetime import datetime
from typing import Dict
from ..models.project import ProjectState
from ..models.spectrum import SpectrumFile


def save_project(
    files: Dict[str, SpectrumFile],
    filepath: str,
    include_arrays: bool = True,
    plot_width_preset: str = "Full"
) -> None:
    """
    Save project state to JSON file.

    Parameters
    ----------
    files : Dict[str, SpectrumFile]
        Dictionary of filename -> SpectrumFile.
    filepath : str
        Output JSON file path.
    include_arrays : bool, default=True
        If False, exclude raw_data and processed_data arrays to reduce file size.
        Note: Project will not be fully restorable without arrays.
    plot_width_preset : str, default="Standard"
        Plot width preset (v2.1+): "Compact", "Standard", "Wide", or "Full".

    Raises
    ------
    ValueError
        If files dict is empty.
    IOError
        If file cannot be written.

    Examples
    --------
    >>> save_project(st.session_state['files'], 'myproject.json',
    ...              plot_width_preset=st.session_state.get('plot_width_preset', 'Standard'))
    """
    if not files:
        raise ValueError("Cannot save empty project (no files loaded)")

    # Create ProjectState
    project = ProjectState(
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        files=files,
        plot_width_preset=plot_width_preset
    )

    # Save to JSON
    project.save_to_json(filepath, include_arrays=include_arrays)


def load_project(filepath: str) -> tuple[Dict[str, SpectrumFile], str]:
    """
    Load project state from JSON file.

    Parameters
    ----------
    filepath : str
        Input JSON file path.

    Returns
    -------
    files : Dict[str, SpectrumFile]
        Dictionary of filename -> SpectrumFile.
    plot_width_preset : str
        Plot width preset (v2.1+). Defaults to "Standard" for v2.0 projects.

    Raises
    ------
    FileNotFoundError
        If file does not exist.
    ValueError
        If JSON is invalid or incompatible version.
    IOError
        If file cannot be read.

    Examples
    --------
    >>> files, plot_width = load_project('myproject.json')
    >>> st.session_state['files'] = files
    >>> st.session_state['plot_width_preset'] = plot_width
    """
    # Load ProjectState
    project = ProjectState.load_from_json(filepath)

    # Validate version compatibility
    validate_version(project.version)

    return project.files, project.plot_width_preset


def validate_version(version: str) -> None:
    """
    Validate project schema version compatibility.

    Parameters
    ----------
    version : str
        Project schema version (semantic versioning: X.Y.Z).

    Raises
    ------
    ValueError
        If version is incompatible with current schema.

    Notes
    -----
    Compatibility rules:
    - Major version must match (1.x.x compatible with 1.y.z)
    - Minor/patch versions are forward/backward compatible

    Examples
    --------
    >>> validate_version("1.0.0")  # OK
    >>> validate_version("2.0.0")  # Raises ValueError
    """
    CURRENT_VERSION = "1.0.0"

    current_major = int(CURRENT_VERSION.split('.')[0])
    project_major = int(version.split('.')[0])

    if project_major != current_major:
        raise ValueError(
            f"Incompatible project version: {version} "
            f"(current version: {CURRENT_VERSION}). "
            f"Major version mismatch - project may have been created with "
            f"an incompatible version of SpectralFit."
        )


def get_project_metadata(filepath: str) -> dict:
    """
    Read project metadata without loading full project.

    Parameters
    ----------
    filepath : str
        Input JSON file path.

    Returns
    -------
    metadata : dict
        Dictionary with keys: version, timestamp, file_count, file_names.

    Examples
    --------
    >>> meta = get_project_metadata('myproject.json')
    >>> print(f"Project saved on {meta['timestamp']}")
    >>> print(f"Contains {meta['file_count']} files: {meta['file_names']}")
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    file_names = [f['filename'] for f in data.get('files', [])]

    return {
        "version": data.get("version", "unknown"),
        "timestamp": data.get("timestamp", "unknown"),
        "file_count": len(data.get("files", [])),
        "file_names": file_names
    }
