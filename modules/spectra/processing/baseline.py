"""
Baseline correction algorithms for spectroscopy data.

This module implements:
- Polynomial baseline fitting and subtraction
- Asymmetric Least Squares (ALS) baseline correction
- Rolling Ball (morphological opening) baseline
- Spline (piecewise cubic) baseline
- airPLS (Adaptive Iteratively Reweighted Penalized Least Squares)
- Peak masking/exclusion for Polynomial and ALS
- Baseline quality metrics

References
----------
- Eilers, P. H. C. & Boelens, H. F. M. (2005).
  "Baseline Correction with Asymmetric Least Squares Smoothing".
  Leiden University Medical Centre Report.
- Zhang, Z. M. et al. (2010). "Baseline correction using adaptive
  iteratively reweighted penalized least squares". Analyst 135:1138-1146.
"""

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from numpy.polynomial import Polynomial
from typing import Tuple


def apply_auto_shift(y: np.ndarray, epsilon: float = 1.0) -> Tuple[np.ndarray, float]:
    """
    Apply automatic vertical shift to ensure non-negative Y values for baseline algorithms.

    This function is used internally to handle negative intensity values in baseline
    correction. The shift is purely for algorithmic stability and does not affect
    the final baseline-corrected output (which remains in original scale).

    Parameters
    ----------
    y : np.ndarray
        Intensity array (may contain negative values).
    epsilon : float, default=1.0
        Small positive buffer added to shift to ensure strict positivity.

    Returns
    -------
    y_shifted : np.ndarray
        Y values shifted to be positive (Y + shift).
    shift : float
        Amount of shift applied (0 if all Y values were already non-negative).

    Notes
    -----
    v2.1+ (FR-13): Automatic Y-shift for baseline correction with negative intensities.

    Algorithm:
    - If min(Y) >= 0: no shift needed, return (Y, 0.0)
    - Otherwise: shift = abs(min(Y)) + epsilon, return (Y + shift, shift)

    Examples
    --------
    >>> y = np.array([-50, -10, 100, 200])
    >>> y_shifted, shift = apply_auto_shift(y, epsilon=1.0)
    >>> print(shift)  # 51.0 (abs(-50) + 1.0)
    >>> print(y_shifted.min())  # 1.0 (now positive)
    """
    y_min = np.min(y)

    if y_min >= 0:
        # No shift needed
        return y, 0.0
    else:
        # Apply shift to make all values positive
        shift = abs(y_min) + epsilon
        return y + shift, shift


def baseline_polynomial_with_autoshift(
    x: np.ndarray,
    y: np.ndarray,
    degree: int = 3
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Polynomial baseline with automatic Y-shift for negative values (v2.1+).

    This is a wrapper around baseline_polynomial() that automatically handles
    negative intensity values by applying an internal shift. The baseline is
    computed on shifted data, but the corrected output is returned in original scale.

    Parameters
    ----------
    x, y, degree : Same as baseline_polynomial()

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity in original Y scale.
    baseline : np.ndarray
        Fitted baseline curve in original Y scale.
    shift : float
        Amount of Y-shift applied (0 if not needed). Logged for transparency.

    Notes
    -----
    See also: baseline_polynomial() for algorithm details.
    v2.1+ (FR-13): Handles negative Y values transparently.
    """
    # Apply automatic shift if needed
    y_shifted, shift = apply_auto_shift(y)

    # Run baseline algorithm on shifted data
    y_corrected_shifted, baseline_shifted = baseline_polynomial(x, y_shifted, degree)

    # Return results in original scale
    # y_corrected = (y + shift) - baseline_shifted = y - (baseline_shifted - shift)
    baseline_original = baseline_shifted - shift
    y_corrected_original = y - baseline_original

    return y_corrected_original, baseline_original, shift


def baseline_polynomial_with_mask(
    x: np.ndarray,
    y: np.ndarray,
    degree: int = 3,
    exclusions: list = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Polynomial baseline with excluded regions (peak masking).

    Parameters
    ----------
    x, y, degree : Same as baseline_polynomial()
    exclusions : list of tuple, optional
        List of (x_min, x_max) ranges to exclude from fitting.
        Baseline will interpolate through these regions.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve (interpolates through excluded regions).
    """
    if exclusions is None or len(exclusions) == 0:
        # No masking, use standard polynomial
        return baseline_polynomial(x, y, degree)

    # Create mask (True = include in fit, False = exclude)
    mask = np.ones(len(x), dtype=bool)
    for x_min, x_max in exclusions:
        mask &= ~((x >= x_min) & (x <= x_max))

    # Fit polynomial only to masked (non-excluded) data
    x_fit = x[mask]
    y_fit = y[mask]

    if len(x_fit) < degree + 1:
        raise ValueError(
            f"Not enough points for degree {degree} polynomial after exclusions. "
            f"Need at least {degree + 1}, got {len(x_fit)}."
        )

    p = Polynomial.fit(x_fit, y_fit, degree)

    # Evaluate baseline over full range (interpolates through excluded regions)
    baseline = p(x)

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline


def baseline_als_with_mask(
    x: np.ndarray,
    y: np.ndarray,
    lambda_: float = 10000.0,
    p: float = 0.001,
    max_iter: int = 10,
    exclusions: list = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    ALS baseline with excluded regions (peak masking).

    Parameters
    ----------
    x, y, lambda_, p, max_iter : Same as baseline_als()
    exclusions : list of tuple, optional
        List of (x_min, x_max) ranges to exclude from fitting.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve.
    """
    if exclusions is None or len(exclusions) == 0:
        # No masking, use standard ALS
        return baseline_als(x, y, lambda_, p, max_iter)

    # Run standard ALS but force zero weight in excluded regions
    n = len(y)

    # Build 2nd derivative operator
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))
    D_T_D = D.T @ D

    # Initialize weights
    w = np.ones(n)

    # Set excluded regions to zero weight (permanent)
    for x_min, x_max in exclusions:
        exclusion_mask = (x >= x_min) & (x <= x_max)
        w[exclusion_mask] = 0.0  # Force zero weight

    # Iterative fitting
    for _ in range(max_iter):
        # Build weighted matrix
        W = sparse.diags(w, 0, shape=(n, n))
        A = W + lambda_ * D_T_D

        # Convert to CSC format for spsolve
        A = A.tocsc()

        # Solve
        baseline = spsolve(A, w * y)

        # Update weights (but keep excluded regions at 0)
        w_new = p * (y > baseline) + (1 - p) * (y <= baseline)

        # Restore zero weights in excluded regions
        for x_min, x_max in exclusions:
            exclusion_mask = (x >= x_min) & (x <= x_max)
            w_new[exclusion_mask] = 0.0

        # Check convergence
        if np.allclose(w, w_new, rtol=1e-4):
            break

        w = w_new

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline


def baseline_polynomial(
    x: np.ndarray,
    y: np.ndarray,
    degree: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit and subtract polynomial baseline from spectrum.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber or wavelength array (1D, float64).
    y : np.ndarray
        Intensity array (1D, float64, same length as x).
    degree : int, default=3
        Polynomial degree (1-10).
        Higher = more flexible (may overfit).
        Recommended: 2-3 for simple backgrounds, 4-6 for complex.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity (y - baseline).
    baseline : np.ndarray
        Fitted baseline curve (same length as x).

    Raises
    ------
    ValueError
        If degree is outside [1, 10] or arrays have different lengths.

    Notes
    -----
    Algorithm (FR-017, FR-019, FR-024):
    - Uses numpy.polynomial.Polynomial.fit() (orthogonal polynomials)
    - Robust to numerical errors for high degrees
    - Suitable for simple fluorescence backgrounds

    For complex baselines with sharp features, consider ALS instead.

    Examples
    --------
    >>> x = np.linspace(0, 1000, 1000)
    >>> y_raw = x * 0.1 + np.sin(x / 100) * 10  # Signal on sloped baseline
    >>> y_corr, baseline = baseline_polynomial(x, y_raw, degree=2)
    >>> print(baseline.shape)
    (1000,)
    """
    # Validation
    if not (1 <= degree <= 10):
        raise ValueError(f"degree must be in [1, 10] (got {degree})")

    if len(x) != len(y):
        raise ValueError(f"x and y must have same length (got {len(x)} vs {len(y)})")

    if len(x) < degree + 1:
        raise ValueError(
            f"Need at least {degree + 1} points for degree {degree} polynomial "
            f"(got {len(x)} points)"
        )

    # Fit polynomial
    p = Polynomial.fit(x, y, degree)

    # Evaluate baseline
    baseline = p(x)

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline


def baseline_als_with_autoshift(
    x: np.ndarray,
    y: np.ndarray,
    lambda_: float = 10000.0,
    p: float = 0.001,
    max_iter: int = 10
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    ALS baseline with automatic Y-shift for negative values (v2.1+).

    This is a wrapper around baseline_als() that automatically handles
    negative intensity values by applying an internal shift. The baseline is
    computed on shifted data, but the corrected output is returned in original scale.

    Parameters
    ----------
    x, y, lambda_, p, max_iter : Same as baseline_als()

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity in original Y scale.
    baseline : np.ndarray
        Fitted baseline curve in original Y scale.
    shift : float
        Amount of Y-shift applied (0 if not needed). Logged for transparency.

    Notes
    -----
    See also: baseline_als() for algorithm details.
    v2.1+ (FR-13): Handles negative Y values transparently.
    """
    # Apply automatic shift if needed
    y_shifted, shift = apply_auto_shift(y)

    # Run baseline algorithm on shifted data
    y_corrected_shifted, baseline_shifted = baseline_als(x, y_shifted, lambda_, p, max_iter)

    # Return results in original scale
    baseline_original = baseline_shifted - shift
    y_corrected_original = y - baseline_original

    return y_corrected_original, baseline_original, shift


def baseline_als(
    x: np.ndarray,
    y: np.ndarray,
    lambda_: float = 10000.0,
    p: float = 0.001,
    max_iter: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Asymmetric Least Squares (ALS) baseline correction.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber or wavelength array (1D, float64).
        Used only for validation; ALS operates on indices.
    y : np.ndarray
        Intensity array (1D, float64).
    lambda_ : float, default=10000.0
        Smoothness parameter (1e3 to 1e6).
        Higher = smoother baseline.
        Recommended: 1e4 for typical Raman/PL.
    p : float, default=0.001
        Asymmetry parameter (0.001 to 0.1).
        Lower = more asymmetric (weights points below baseline).
        Recommended: 0.001-0.01 for fluorescence removal.
    max_iter : int, default=10
        Maximum iterations for convergence.
        Typically converges in 5-10 iterations.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity (y - baseline).
    baseline : np.ndarray
        Fitted baseline curve (same length as x).

    Raises
    ------
    ValueError
        If parameters are outside valid ranges.

    Notes
    -----
    Algorithm (FR-018, FR-019, FR-024):
    - Iteratively fits smooth curve that preferentially weights points
      below the current estimate (asymmetric weighting)
    - Uses sparse matrix solver for efficiency
    - Excellent for removing broad fluorescence backgrounds

    The algorithm minimizes:
        ||W(y - z)||² + λ||Dz||²
    where W is asymmetric weight matrix, D is 2nd derivative operator,
    and z is the baseline.

    Examples
    --------
    >>> y_corr, baseline = baseline_als(x, y, lambda_=1e4, p=0.001)
    >>> print(f"Baseline range: {baseline.min():.1f} - {baseline.max():.1f}")

    References
    ----------
    Eilers & Boelens (2005), "Baseline Correction with Asymmetric Least Squares"
    """
    # Validation
    if len(x) != len(y):
        raise ValueError(f"x and y must have same length (got {len(x)} vs {len(y)})")

    if not (1000.0 <= lambda_ <= 1000000.0):
        raise ValueError(f"lambda_ must be in [1e3, 1e6] (got {lambda_})")

    if not (0.001 <= p <= 0.1):
        raise ValueError(f"p must be in [0.001, 0.1] (got {p})")

    if max_iter < 1:
        raise ValueError(f"max_iter must be >= 1 (got {max_iter})")

    n = len(y)

    if n < 10:
        raise ValueError(f"Need at least 10 points for ALS (got {n})")

    # Build 2nd derivative operator (sparse matrix)
    # D is (n-2) x n matrix
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))

    # Precompute D^T * D
    D_T_D = D.T @ D

    # Initialize weights (all equal initially)
    w = np.ones(n)

    # Iterative fitting
    for _ in range(max_iter):
        # Build weighted matrix: W + λD^T*D
        W = sparse.diags(w, 0, shape=(n, n))
        A = W + lambda_ * D_T_D

        # Convert to CSC format for spsolve
        A = A.tocsc()

        # Solve: (W + λD^T*D) z = W y
        baseline = spsolve(A, w * y)

        # Update weights (asymmetric)
        # Points above baseline get low weight (p)
        # Points below baseline get high weight (1-p)
        w_new = p * (y > baseline) + (1 - p) * (y <= baseline)

        # Check convergence
        if np.allclose(w, w_new, rtol=1e-4):
            break

        w = w_new

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline
def baseline_rolling_ball(
    x: np.ndarray,
    y: np.ndarray,
    radius: float = 50.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Rolling ball baseline correction (morphological opening).

    Simulates rolling a ball of specified radius under the spectrum.
    Excellent for spectra with many sharp peaks.

    Parameters
    ----------
    x : np.ndarray
        X values (wavelength or wavenumber).
    y : np.ndarray
        Y values (intensity).
    radius : float, default=50.0
        Ball radius in X units (cm⁻¹ or nm).
        Larger radius = smoother baseline.
        Typical: 20-100 cm⁻¹ for Raman, 50-200 nm for PL.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve.

    Notes
    -----
    Algorithm: Morphological opening (erosion followed by dilation).
    The "ball" rolls under the spectrum, and the baseline is the top
    of the ball trajectory.

    Example
    -------
    >>> y_corrected, baseline = baseline_rolling_ball(x, y, radius=50)
    """
    from scipy.ndimage import grey_opening

    # Validation
    if radius <= 0:
        raise ValueError(f"radius must be > 0 (got {radius})")

    # Convert radius to data points
    dx = np.median(np.abs(np.diff(x)))
    if dx == 0:
        raise ValueError("X values must not be constant")

    ball_size = int(np.round(radius / dx))
    if ball_size < 1:
        ball_size = 1  # Minimum size
    elif ball_size > len(y) // 2:
        raise ValueError(
            f"Ball radius ({radius}) is too large for data range. "
            f"Max recommended: {(len(y) // 2) * dx:.1f}"
        )

    # Morphological opening (erosion + dilation)
    baseline = grey_opening(y, size=ball_size)

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline


def baseline_spline(
    x: np.ndarray,
    y: np.ndarray,
    smoothness: float = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Piecewise cubic spline baseline correction.

    Fits a smoothing spline to the data with automatic knot placement.
    Provides local control without global oscillations.

    Parameters
    ----------
    x : np.ndarray
        X values (wavelength or wavenumber).
    y : np.ndarray
        Y values (intensity).
    smoothness : float, optional
        Smoothing factor (s parameter for UnivariateSpline).
        If None, uses s = len(x) * var(y) (automatic).
        Larger = smoother baseline.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve.

    Notes
    -----
    Uses scipy's UnivariateSpline with automatic knot placement.
    The smoothing factor balances fit quality vs. smoothness.

    Example
    -------
    >>> y_corrected, baseline = baseline_spline(x, y)
    """
    from scipy.interpolate import UnivariateSpline

    # Auto-calculate smoothness if not provided
    if smoothness is None:
        smoothness = len(x) * np.var(y)

    # Validation
    if smoothness < 0:
        raise ValueError(f"smoothness must be >= 0 (got {smoothness})")

    # Fit smoothing spline (k=3 for cubic, s=smoothness)
    spline = UnivariateSpline(x, y, k=3, s=smoothness)
    baseline = spline(x)

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline


def baseline_airpls(
    x: np.ndarray,
    y: np.ndarray,
    lambda_: float = 100000.0,
    max_iter: int = 15,
    tol: float = 1e-3
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Adaptive Iteratively Reweighted Penalized Least Squares (airPLS) baseline.

    Improved ALS that adapts weights automatically without manual p parameter.
    Self-optimizing for peak suppression.

    Parameters
    ----------
    x : np.ndarray
        X values (wavelength or wavenumber).
    y : np.ndarray
        Y values (intensity).
    lambda_ : float, default=100000.0
        Smoothness parameter (10³ - 10⁶).
        Higher = smoother baseline.
    max_iter : int, default=15
        Maximum iterations.
    tol : float, default=1e-3
        Convergence tolerance for negative residuals.

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve.

    Notes
    -----
    Reference: Zhang et al. (2010), Analyst 135:1138-1146.
    Adaptive weight formula eliminates the need for manual p tuning.

    Algorithm:
    - Initialize weights w = 1
    - Iterate:
        - Solve (W + λD^T*D) z = W*y
        - Update weights: w_i = 0 if residual > 0, else exp(-residual²/σ²)
        - Stop if sum(negative residuals) < tol

    Example
    -------
    >>> y_corrected, baseline = baseline_airpls(x, y, lambda_=1e5)
    """
    # Validation
    if not (1000.0 <= lambda_ <= 10000000.0):
        raise ValueError(f"lambda_ must be in [1e3, 1e7] (got {lambda_})")

    n = len(y)

    # Build 2nd derivative operator
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))
    D_T_D = D.T @ D

    # Initialize weights
    w = np.ones(n)

    # Iterative fitting
    for iteration in range(max_iter):
        # Build weighted matrix
        W = sparse.diags(w, 0, shape=(n, n))
        A = W + lambda_ * D_T_D

        # Convert to CSC format for spsolve
        A = A.tocsc()

        # Solve: (W + λD^T*D) z = W*y
        baseline = spsolve(A, w * y)

        # Calculate residuals
        residuals = y - baseline

        # Adaptive weight update
        # Positive residuals (peaks) → zero weight
        # Negative residuals (baseline) → adaptive weight based on magnitude
        neg_residuals = residuals[residuals < 0]

        if len(neg_residuals) > 0:
            # Standard deviation of negative residuals
            sigma = np.std(neg_residuals)

            # Adaptive weights: exp(-k * residual² / σ²)
            # k = 2 for moderate suppression
            w_new = np.where(
                residuals >= 0,
                0.0,  # Zero weight for positive residuals (peaks)
                np.exp(-2 * (residuals ** 2) / (sigma ** 2 + 1e-10))  # Adaptive for negative
            )
        else:
            # All residuals positive (unlikely), use uniform small weights
            w_new = np.ones(n) * 0.01

        # Check convergence: sum of negative residuals should approach zero
        neg_sum = np.sum(np.abs(neg_residuals)) if len(neg_residuals) > 0 else 0
        if neg_sum < tol * n:
            break

        w = w_new

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline


def calculate_baseline_quality_metrics(
    y: np.ndarray,
    baseline: np.ndarray,
    x: np.ndarray = None
) -> dict:
    """
    Calculate quality metrics for baseline correction.

    Parameters
    ----------
    y : np.ndarray
        Original intensity values.
    baseline : np.ndarray
        Fitted baseline curve.
    x : np.ndarray, optional
        X values (for roughness calculation in X units).

    Returns
    -------
    metrics : dict
        Dictionary with quality metrics:
        - residual_std: Standard deviation of (y - baseline)
        - residual_mean: Mean of (y - baseline)
        - roughness: Sum of squared 2nd derivative (baseline curvature)
        - peak_count: Estimated number of peaks above baseline
        - baseline_range: (min, max) of baseline values

    Notes
    -----
    Lower residual_std = better fit (but may indicate overfitting).
    Lower roughness = smoother baseline (more desirable).
    Higher peak_count = more features preserved above baseline.

    Example
    -------
    >>> metrics = calculate_baseline_quality_metrics(y, baseline)
    >>> print(f"Residual Std: {metrics['residual_std']:.2f}")
    """
    # Residuals
    residuals = y - baseline
    residual_std = np.std(residuals)
    residual_mean = np.mean(residuals)

    # Baseline roughness (2nd derivative squared)
    d2_baseline = np.diff(baseline, n=2)  # 2nd derivative
    roughness = np.sum(d2_baseline ** 2)

    # Normalize roughness by baseline range if X provided
    if x is not None:
        dx = np.median(np.abs(np.diff(x)))
        roughness = roughness / (dx ** 4)  # Scale by dx^4 (2nd deriv has dx^-2)

    # Estimate peak count above baseline
    y_corrected = residuals
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(y_corrected, prominence=residual_std * 2)  # Peaks > 2σ
    peak_count = len(peaks)

    # Baseline range
    baseline_min = np.min(baseline)
    baseline_max = np.max(baseline)

    return {
        "residual_std": residual_std,
        "residual_mean": residual_mean,
        "roughness": roughness,
        "peak_count": peak_count,
        "baseline_range": (baseline_min, baseline_max)
    }
