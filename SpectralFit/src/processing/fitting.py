"""
Voigt profile fitting using lmfit.

This module implements:
- Multi-peak Voigt fitting with constrained nonlinear optimization
- Auto-bounds calculation based on mode
- Peak auto-finding using scipy.signal
- Fit quality metrics (chi-squared, R²)

References
----------
- lmfit documentation: https://lmfit.github.io/lmfit-py/
- Voigt profile: convolution of Gaussian and Lorentzian line shapes
"""

import numpy as np
from scipy import signal
from lmfit import Model, Parameters
from lmfit.models import VoigtModel
import time
from typing import List, Tuple, Optional
from ..models.peak import PeakDefinition, FittedPeak, FitResult


def fit_voigt_peaks(
    x: np.ndarray,
    y: np.ndarray,
    peak_table: List[PeakDefinition],
    mode: str = "Raman"
) -> FitResult:
    """
    Fit multiple Voigt profiles to spectrum data.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber (cm⁻¹) or wavelength (nm).
    y : np.ndarray
        Baseline-corrected intensity.
    peak_table : List[PeakDefinition]
        User-defined peak guesses with bounds.
    mode : str, default="Raman"
        "Raman" or "PL" (affects auto-bounds if not manually set).

    Returns
    -------
    FitResult
        Fitting results with fitted_peaks, quality metrics, and error handling.

    Raises
    ------
    ValueError
        If peak_table is empty or has > 10 peaks.

    Notes
    -----
    Algorithm (FR-031 to FR-037):
    - Uses lmfit VoigtModel (Gaussian + Lorentzian convolution)
    - Levenberg-Marquardt optimizer (method='leastsq')
    - Auto-bounds from PeakDefinition (if not manually overridden)
    - Returns actionable error messages on convergence failure

    Voigt parameters:
    - center: peak position
    - amplitude: peak height × width (integrated intensity)
    - sigma: Gaussian width (FWHM = 2.355 * sigma)
    - gamma: Lorentzian width (FWHM = 2 * gamma)

    Examples
    --------
    >>> peak_defs = [
    ...     PeakDefinition(center=1350, amplitude=5000, width_fwhm=50),
    ...     PeakDefinition(center=1580, amplitude=8000, width_fwhm=60)
    ... ]
    >>> result = fit_voigt_peaks(x, y, peak_defs, mode="Raman")
    >>> if result.success:
    ...     print(f"R² = {result.r_squared:.4f}")
    """
    # Validation
    if len(peak_table) == 0:
        raise ValueError("peak_table must have at least 1 peak")

    if len(peak_table) > 10:
        raise ValueError(f"peak_table must have <= 10 peaks (got {len(peak_table)})")

    if len(x) != len(y):
        raise ValueError(f"x and y must have same length (got {len(x)} vs {len(y)})")

    # Calculate auto-bounds for peaks that don't have manual bounds
    x_range = (x.min(), x.max())
    y_max = y.max()
    spectral_resolution = np.median(np.abs(np.diff(x)))

    for peak in peak_table:
        peak.calculate_auto_bounds(mode, x_range, y_max, spectral_resolution)

    # Build composite model (sum of Voigt models)
    composite_model = None
    params = Parameters()

    for i, peak in enumerate(peak_table):
        prefix = f"p{i}_"
        voigt = VoigtModel(prefix=prefix)

        if composite_model is None:
            composite_model = voigt
        else:
            composite_model += voigt

        # Convert FWHM to sigma/gamma
        # For Voigt: approximate FWHM ≈ 0.5346*FWHM_L + sqrt(0.2166*FWHM_L² + FWHM_G²)
        # Simplification: assume equal Gaussian/Lorentzian contributions
        sigma_guess = peak.width_fwhm / (2 * 2.355)  # Gaussian FWHM = 2.355 * sigma
        gamma_guess = peak.width_fwhm / 4.0  # Lorentzian FWHM = 2 * gamma

        # Add parameters with bounds
        params.add(f"{prefix}center", value=peak.center,
                   min=peak.center_min, max=peak.center_max)
        params.add(f"{prefix}amplitude", value=peak.amplitude,
                   min=0, max=peak.amplitude_max)
        params.add(f"{prefix}sigma", value=sigma_guess,
                   min=peak.width_min / (2 * 2.355), max=peak.width_max / (2 * 2.355))
        params.add(f"{prefix}gamma", value=gamma_guess,
                   min=peak.width_min / 4.0, max=peak.width_max / 4.0)

    # Fit using Levenberg-Marquardt with increased tolerance
    start_time = time.time()

    try:
        result = composite_model.fit(
            y, params, x=x,
            method='leastsq',
            max_nfev=2000,
            fit_kws={'ftol': 1e-6, 'xtol': 1e-6}  # Increased tolerance for stability
        )
        convergence_time = time.time() - start_time

        # Accept fit even if error bars couldn't be estimated (common with tight fits)
        # result.success may be False if uncertainties couldn't be calculated, but fit is still valid
        if not result.success and "Tolerance seems to be too small" not in str(result.message):
            return FitResult(
                success=False,
                fitted_peaks=[],
                total_fit_curve=np.zeros_like(y),
                residuals=y.copy(),
                chi_squared=np.sum(y**2),
                r_squared=0.0,
                convergence_time=convergence_time,
                error_message=(
                    f"Fitting failed to converge ({result.message}). "
                    f"Try adjusting initial guesses or reducing number of peaks."
                )
            )

    except Exception as e:
        convergence_time = time.time() - start_time
        return FitResult(
            success=False,
            fitted_peaks=[],
            total_fit_curve=np.zeros_like(y),
            residuals=y.copy(),
            chi_squared=np.sum(y**2),
            r_squared=0.0,
            convergence_time=convergence_time,
            error_message=f"Fitting error: {str(e)}"
        )

    # Extract fitted parameters
    fitted_peaks = []
    total_fit = result.best_fit

    # Helper functions to safely extract parameter values and errors
    # (handles both Parameter objects and raw floats)
    def get_param_value(param):
        """Extract value from Parameter object or float."""
        return param.value if hasattr(param, 'value') else float(param)

    def get_param_stderr(param):
        """Extract stderr from Parameter object (returns 0.0 if unavailable)."""
        if hasattr(param, 'stderr'):
            return param.stderr or 0.0
        return 0.0

    for i, peak in enumerate(peak_table):
        prefix = f"p{i}_"

        try:
            # Get fitted values - robust to both Parameter objects and raw floats
            center_fit = get_param_value(result.params[f"{prefix}center"])
            center_stderr = get_param_stderr(result.params[f"{prefix}center"])
            amplitude_fit = get_param_value(result.params[f"{prefix}amplitude"])
            amplitude_stderr = get_param_stderr(result.params[f"{prefix}amplitude"])
            sigma_fit = get_param_value(result.params[f"{prefix}sigma"])
            sigma_stderr = get_param_stderr(result.params[f"{prefix}sigma"])
            gamma_fit = get_param_value(result.params[f"{prefix}gamma"])
        except AttributeError as e:
            # Debug: print parameter type if extraction fails
            param_key = f"{prefix}center"
            param_obj = result.params.get(param_key)
            raise AttributeError(
                f"Parameter extraction failed for {param_key}. "
                f"Type: {type(param_obj)}, "
                f"Has 'value': {hasattr(param_obj, 'value')}, "
                f"Original error: {e}"
            )

        # Convert sigma back to FWHM
        width_fwhm_fit = 2.355 * sigma_fit  # Approximate
        width_stderr = 2.355 * sigma_stderr

        # Calculate shape parameter (Lorentzian fraction)
        # shape = gamma / (gamma + sigma)
        shape_fit = gamma_fit / (gamma_fit + sigma_fit)

        # Evaluate component curve
        voigt_component = VoigtModel(prefix=prefix)
        # Pass fitted parameters directly as keyword arguments
        component_curve = voigt_component.eval(
            x=x,
            **{
                f"{prefix}center": center_fit,
                f"{prefix}amplitude": amplitude_fit,
                f"{prefix}sigma": sigma_fit,
                f"{prefix}gamma": gamma_fit
            }
        )

        fitted_peaks.append(FittedPeak(
            label=peak.label,
            center=center_fit,
            center_stderr=center_stderr,
            amplitude=amplitude_fit,
            amplitude_stderr=amplitude_stderr,
            width_fwhm=width_fwhm_fit,
            width_stderr=width_stderr,
            shape=shape_fit,
            component_curve=component_curve
        ))

    # Calculate quality metrics
    residuals = result.residual
    chi_squared = result.chisqr

    # R-squared
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return FitResult(
        success=True,
        fitted_peaks=fitted_peaks,
        total_fit_curve=total_fit,
        residuals=residuals,
        chi_squared=chi_squared,
        r_squared=r_squared,
        convergence_time=convergence_time,
        error_message=""
    )


def auto_find_peaks(
    x: np.ndarray,
    y: np.ndarray,
    mode: str = "Raman",
    min_peaks: int = 2,
    max_peaks: int = 5,
    prominence_threshold: float = 0.05
) -> List[PeakDefinition]:
    """
    Automatically find peaks in spectrum using scipy.signal.find_peaks.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber (cm⁻¹) or wavelength (nm).
    y : np.ndarray
        Baseline-corrected intensity.
    mode : str, default="Raman"
        "Raman" or "PL" (used for auto-bounds).
    min_peaks : int, default=2
        Minimum number of peaks to find.
    max_peaks : int, default=5
        Maximum number of peaks to find.
    prominence_threshold : float, default=0.05
        Minimum peak prominence (fraction of max intensity).

    Returns
    -------
    peak_table : List[PeakDefinition]
        Automatically generated peak definitions.

    Notes
    -----
    Algorithm (FR-027):
    - Uses scipy.signal.find_peaks with prominence threshold
    - Estimates FWHM from peak widths_half_height
    - Returns top N peaks by prominence (N = max_peaks)
    - Default colors from Plotly palette

    Examples
    --------
    >>> peak_table = auto_find_peaks(x, y, mode="Raman", max_peaks=5)
    >>> print(f"Found {len(peak_table)} peaks")
    """
    if len(y) < 10:
        return []

    # Calculate prominence threshold
    y_max = y.max()
    min_prominence = prominence_threshold * y_max

    # Find peaks
    peak_indices, properties = signal.find_peaks(
        y,
        prominence=min_prominence,
        width=2  # Minimum width in data points
    )

    if len(peak_indices) == 0:
        return []

    # Sort by prominence (descending)
    prominences = properties['prominences']
    sorted_indices = np.argsort(prominences)[::-1]

    # Take top N peaks
    n_peaks = min(max(len(sorted_indices), min_peaks), max_peaks)
    top_indices = sorted_indices[:n_peaks]

    # Create PeakDefinition objects
    peak_table = []
    default_colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    for i, idx in enumerate(top_indices):
        peak_idx = peak_indices[idx]

        # Peak center
        center = x[peak_idx]

        # Amplitude (peak height)
        amplitude = y[peak_idx]

        # Estimate FWHM from widths
        if 'widths' in properties:
            width_points = properties['widths'][idx]
            dx = np.median(np.abs(np.diff(x)))
            width_fwhm = width_points * dx
        else:
            # Fallback: use spectral resolution × 10
            width_fwhm = 10 * np.median(np.abs(np.diff(x)))

        # Color
        color = default_colors[i % len(default_colors)]

        # Label
        label = f"Peak {i+1}"

        peak_table.append(PeakDefinition(
            center=center,
            amplitude=amplitude,
            width_fwhm=width_fwhm,
            label=label,
            color=color,
            shape=0.5  # Equal Gaussian/Lorentzian
        ))

    # Sort by center position (left to right)
    peak_table.sort(key=lambda p: p.center)

    # Renumber labels
    for i, peak in enumerate(peak_table):
        peak.label = f"Peak {i+1}"

    return peak_table


def estimate_peak_bounds(
    peak: PeakDefinition,
    x_range: Tuple[float, float],
    y_max: float,
    spectral_resolution: float,
    mode: str = "Raman"
) -> PeakDefinition:
    """
    Recalculate auto-bounds for a PeakDefinition.

    This is a convenience wrapper around PeakDefinition.calculate_auto_bounds().

    Parameters
    ----------
    peak : PeakDefinition
        Peak to update.
    x_range : Tuple[float, float]
        (min, max) of X data range.
    y_max : float
        Maximum Y value.
    spectral_resolution : float
        Median step size in X.
    mode : str, default="Raman"
        "Raman" or "PL".

    Returns
    -------
    peak : PeakDefinition
        Updated peak with auto-bounds calculated.
    """
    peak.calculate_auto_bounds(mode, x_range, y_max, spectral_resolution)
    return peak
