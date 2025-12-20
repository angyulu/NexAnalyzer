"""
Data models for project state and styling preferences.

This module defines:
- StylingPreferences: Global plot styling settings
- ProjectState: Complete session state for JSON persistence
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
import json


@dataclass
class StylingPreferences:
    """
    Global plot styling preferences.

    Attributes
    ----------
    data_color : str
        Hex color for data scatter plot (default: Plotly blue).
    data_line_width : float
        Line width in points (0.5-5.0).
    data_marker_style : Literal["markers", "lines", "markers+lines"]
        Plot mode for data points.
    fit_color : str
        Hex color for total fit curve (default: Plotly orange).
    fit_line_width : float
        Line width for total fit (0.5-5.0).
    fit_line_style : Literal["solid", "dash", "dot"]
        Line style for total fit.
    residual_color : str
        Hex color for residual subplot (default: Plotly red).
    peak_colors : list[str]
        Colors for individual peak components (Plotly default palette).
    """

    data_color: str = "#1f77b4"
    data_line_width: float = 2.0
    data_marker_style: Literal["markers", "lines", "markers+lines"] = "markers"
    fit_color: str = "#ff7f0e"
    fit_line_width: float = 2.5
    fit_line_style: Literal["solid", "dash", "dot"] = "solid"
    residual_color: str = "#d62728"
    peak_colors: list[str] = field(default_factory=lambda: [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ])

    def __post_init__(self):
        """Validate attributes."""
        if not (0.5 <= self.data_line_width <= 5.0):
            raise ValueError(f"data_line_width must be in [0.5, 5.0] (got {self.data_line_width})")

        if not (0.5 <= self.fit_line_width <= 5.0):
            raise ValueError(f"fit_line_width must be in [0.5, 5.0] (got {self.fit_line_width})")

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "data_color": self.data_color,
            "data_line_width": self.data_line_width,
            "data_marker_style": self.data_marker_style,
            "fit_color": self.fit_color,
            "fit_line_width": self.fit_line_width,
            "fit_line_style": self.fit_line_style,
            "residual_color": self.residual_color,
            "peak_colors": self.peak_colors
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StylingPreferences":
        """Deserialize from dictionary."""
        return cls(**data)


@dataclass
class ProjectState:
    """
    Complete session state for JSON persistence.

    Attributes
    ----------
    version : str
        Semantic version of project schema (e.g., '1.0.0').
    timestamp : str
        ISO 8601 timestamp of project save.
    files : dict[str, SpectrumFile]
        Dictionary mapping filename to SpectrumFile object.
    global_styling : StylingPreferences
        Global plot styling preferences.
    plot_width_preset : str
        Plot width preset (v2.1+): "Compact", "Standard", "Wide", or "Full".
    """

    version: str
    timestamp: str
    files: dict
    global_styling: StylingPreferences = field(default_factory=StylingPreferences)
    plot_width_preset: str = "Standard"

    def __post_init__(self):
        """Validate attributes."""
        # Version must be semantic (X.Y.Z)
        parts = self.version.split('.')
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"version must be semantic X.Y.Z (got {self.version})")

        # Must have at least 1 file
        if not (1 <= len(self.files) <= 100):
            raise ValueError(f"files must have 1-100 entries (got {len(self.files)})")

        # Timestamp should be ISO 8601
        try:
            datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"timestamp must be ISO 8601 format (got {self.timestamp})")

    def to_dict(self, include_arrays: bool = True) -> dict:
        """
        Serialize to dictionary for JSON export.

        Parameters
        ----------
        include_arrays : bool
            If False, exclude raw_data and processed_data arrays to reduce file size.
        """
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "files": [f.to_dict(include_arrays=include_arrays) for f in self.files.values()],
            "global_styling": self.global_styling.to_dict(),
            "plot_width_preset": self.plot_width_preset
        }

    def save_to_json(self, filepath: str, include_arrays: bool = True):
        """
        Save project state to JSON file.

        Parameters
        ----------
        filepath : str
            Output JSON file path.
        include_arrays : bool
            If False, exclude data arrays to reduce file size.
        """
        data = self.to_dict(include_arrays=include_arrays)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectState":
        """Deserialize from dictionary (with v2.0 backward compatibility)."""
        from .spectrum import SpectrumFile

        files_dict = {
            f["filename"]: SpectrumFile.from_dict(f)
            for f in data["files"]
        }

        # v2.1: Add default for plot_width_preset if missing (v2.0 compatibility)
        plot_width_preset = data.get("plot_width_preset", "Standard")

        return cls(
            version=data["version"],
            timestamp=data["timestamp"],
            files=files_dict,
            global_styling=StylingPreferences.from_dict(data.get("global_styling", {})),
            plot_width_preset=plot_width_preset
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "ProjectState":
        """
        Load project state from JSON file.

        Parameters
        ----------
        filepath : str
            Input JSON file path.

        Returns
        -------
        ProjectState
            Loaded project state.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
