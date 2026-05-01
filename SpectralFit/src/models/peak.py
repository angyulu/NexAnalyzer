"""
Data models for peak definitions and fit results.

This module defines:
- PeakDefinition: User-defined peak guess with auto-calculated bounds
- FittedPeak: Fitted parameters with standard errors
- FitResult: Complete fitting results with quality metrics
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class PeakDefinition:
    """
    User-defined peak guess with fitting bounds.

    Attributes
    ----------
    center : float
        Peak center position (cm⁻¹ or nm).
    amplitude : float
        Placeholder field; required > 0 for backward-compatible serialization.
        The runtime initial guess is auto-estimated from data at fit time, and
        ``amplitude_max`` is derived from ``y_max`` (5× max intensity), so this
        value is not consulted by the fitter. Optional in the Excel preset
        format (defaults to 1.0 when absent).
    width_fwhm : float
        Full-width-at-half-maximum (cm⁻¹ or nm, must be > 0).
    label : str
        User-defined label (e.g., 'D-Band'), max 50 characters.
    shape : float
        Voigt mixing parameter (0=Gaussian, 1=Lorentzian), range [0, 1].
    color : str
        Hex color for plot component (e.g., '#1f77b4').
    center_min : Optional[float]
        Lower bound for center (auto-calculated if None).
    center_max : Optional[float]
        Upper bound for center (auto-calculated if None).
    width_min : Optional[float]
        Minimum FWHM (auto-calculated if None).
    width_max : Optional[float]
        Maximum FWHM (auto-calculated if None).
    amplitude_max : Optional[float]
        Maximum amplitude (auto-calculated if None).
    """

    center: float
    amplitude: float
    width_fwhm: float
    label: str = ""
    shape: float = 0.5
    color: str = "#1f77b4"
    center_min: Optional[float] = None
    center_max: Optional[float] = None
    width_min: Optional[float] = None
    width_max: Optional[float] = None
    amplitude_max: Optional[float] = None

    def __post_init__(self):
        """Validate attributes."""
        if self.amplitude <= 0:
            raise ValueError(f"amplitude must be > 0 (got {self.amplitude})")

        if self.width_fwhm <= 0:
            raise ValueError(f"width_fwhm must be > 0 (got {self.width_fwhm})")

        if len(self.label) > 50:
            raise ValueError(f"label must be <= 50 characters (got {len(self.label)})")

        if not (0.0 <= self.shape <= 1.0):
            raise ValueError(f"shape must be in [0, 1] (got {self.shape})")

        # Validate hex color format
        if not (self.color.startswith('#') and len(self.color) == 7):
            raise ValueError(f"color must be hex format #RRGGBB (got {self.color})")

    def calculate_auto_bounds(
        self,
        mode: str,
        x_range: tuple[float, float],
        y_max: float,
        spectral_resolution: float
    ):
        """
        Calculate auto-bounds based on mode and data characteristics.

        Parameters
        ----------
        mode : str
            'Raman' or 'PL' (affects center tolerance).
        x_range : tuple[float, float]
            (min, max) of X data range.
        y_max : float
            Maximum Y value in data.
        spectral_resolution : float
            Median step size in X (used for width_min).

        Notes
        -----
        Auto-bounds logic (FR-029):
        - Raman: center ± 5 cm⁻¹
        - PL: center ± 30 nm
        - width_min: 2-3 × spectral_resolution
        - width_max: 50% of X range
        - amplitude_max: 2 × max(Y)
        """
        # Center bounds (adaptive: wider tolerance for broader peaks)
        if mode == "Raman":
            # Raman: at least 5 cm⁻¹ or 5% of FWHM, whichever is larger
            center_tolerance = max(5.0, 0.05 * self.width_fwhm)
        else:  # PL
            # PL: at least 30 nm or 10% of FWHM, whichever is larger
            center_tolerance = max(30.0, 0.10 * self.width_fwhm)

        # Always recalculate center bounds to ensure they include the current center
        # (important when user manually edits peak positions)
        self.center_min = max(x_range[0], self.center - center_tolerance)
        self.center_max = min(x_range[1], self.center + center_tolerance)

        # Width bounds (adaptive: allow 0.5× to 3× initial guess)
        # Always recalculate to ensure bounds match current width_fwhm
        # At least 2.5× spectral resolution, or 50% of initial guess
        self.width_min = max(2.5 * spectral_resolution, 0.5 * self.width_fwhm)
        # At most 50% of X range, or 3× initial guess (prevents runaway fitting)
        self.width_max = min(0.5 * (x_range[1] - x_range[0]), 3.0 * self.width_fwhm)

        # Amplitude bounds (wider range for uncertain peaks)
        if self.amplitude_max is None:
            # Allow up to 5× max intensity (accounts for sharp peaks above baseline)
            self.amplitude_max = 5.0 * y_max

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "label": self.label,
            "center": self.center,
            "amplitude": self.amplitude,
            "width_fwhm": self.width_fwhm,
            "shape": self.shape,
            "color": self.color,
            "center_min": self.center_min,
            "center_max": self.center_max,
            "width_min": self.width_min,
            "width_max": self.width_max,
            "amplitude_max": self.amplitude_max
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PeakDefinition":
        """Deserialize from dictionary."""
        return cls(**data)


@dataclass
class FittedPeak:
    """
    Fitted peak parameters with standard errors.

    Attributes
    ----------
    label : str
        Copied from PeakDefinition.
    center : float
        Fitted peak center (cm⁻¹ or nm).
    center_stderr : float
        Standard error in center from lmfit covariance.
    amplitude : float
        Fitted amplitude (raw units).
    amplitude_stderr : float
        Standard error in amplitude.
    width_fwhm : float
        Fitted FWHM (cm⁻¹ or nm).
    width_stderr : float
        Standard error in FWHM.
    shape : float
        Fitted Voigt mixing (0-1).
    component_curve : np.ndarray
        This peak's contribution to total fit (same length as X).
    color : str
        Peak color for plotting (hex #RRGGBB), copied from PeakDefinition.
    """

    label: str
    center: float
    center_stderr: float
    amplitude: float
    amplitude_stderr: float
    width_fwhm: float
    width_stderr: float
    shape: float
    component_curve: np.ndarray
    color: str = "#1f77b4"  # Default color

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "label": self.label,
            "center": self.center,
            "center_stderr": self.center_stderr,
            "amplitude": self.amplitude,
            "amplitude_stderr": self.amplitude_stderr,
            "width_fwhm": self.width_fwhm,
            "width_stderr": self.width_stderr,
            "shape": self.shape,
            "component_curve": self.component_curve.tolist() if self.component_curve is not None else None,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FittedPeak":
        """Deserialize from dictionary."""
        component_curve = np.array(data["component_curve"]) if data.get("component_curve") else None
        return cls(
            label=data["label"],
            center=data["center"],
            center_stderr=data["center_stderr"],
            amplitude=data["amplitude"],
            amplitude_stderr=data["amplitude_stderr"],
            width_fwhm=data["width_fwhm"],
            width_stderr=data["width_stderr"],
            shape=data["shape"],
            component_curve=component_curve,
            color=data.get("color", "#1f77b4")  # Default color if not present
        )


@dataclass
class FitResult:
    """
    Complete fitting results with quality metrics.

    Attributes
    ----------
    success : bool
        True if Levenberg-Marquardt solver converged.
    fitted_peaks : list[FittedPeak]
        Fitted parameters for each peak (1-10 peaks).
    total_fit_curve : np.ndarray
        Sum of all fitted peaks (same length as X).
    residuals : np.ndarray
        Y_data - total_fit_curve.
    chi_squared : float
        Sum of squared residuals.
    r_squared : float
        Coefficient of determination (0-1).
    convergence_time : float
        Fitting time in seconds.
    error_message : str
        Empty if success=True, else actionable suggestion.
    """

    success: bool
    fitted_peaks: list[FittedPeak]
    total_fit_curve: np.ndarray
    residuals: np.ndarray
    chi_squared: float
    r_squared: float
    convergence_time: float
    error_message: str = ""

    def __post_init__(self):
        """Validate attributes."""
        # Allow empty fitted_peaks only if success=False
        if self.success and not (1 <= len(self.fitted_peaks) <= 10):
            raise ValueError(f"fitted_peaks must have 1-10 peaks when success=True (got {len(self.fitted_peaks)})")

        if not (0.0 <= self.r_squared <= 1.0):
            raise ValueError(f"r_squared must be in [0, 1] (got {self.r_squared})")

        if self.chi_squared < 0:
            raise ValueError(f"chi_squared must be >= 0 (got {self.chi_squared})")

        if self.convergence_time < 0:
            raise ValueError(f"convergence_time must be >= 0 (got {self.convergence_time})")

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "success": self.success,
            "fitted_peaks": [p.to_dict() for p in self.fitted_peaks],
            "total_fit_curve": self.total_fit_curve.tolist() if self.total_fit_curve is not None else None,
            "residuals": self.residuals.tolist() if self.residuals is not None else None,
            "chi_squared": self.chi_squared,
            "r_squared": self.r_squared,
            "convergence_time": self.convergence_time,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FitResult":
        """Deserialize from dictionary."""
        return cls(
            success=data["success"],
            fitted_peaks=[FittedPeak.from_dict(p) for p in data["fitted_peaks"]],
            total_fit_curve=np.array(data["total_fit_curve"]) if data.get("total_fit_curve") else None,
            residuals=np.array(data["residuals"]) if data.get("residuals") else None,
            chi_squared=data["chi_squared"],
            r_squared=data["r_squared"],
            convergence_time=data["convergence_time"],
            error_message=data.get("error_message", "")
        )
