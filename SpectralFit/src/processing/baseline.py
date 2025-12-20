"""
Baseline correction algorithms for spectroscopy data.

This module implements:
- Polynomial baseline fitting and subtraction
- Asymmetric Least Squares (ALS) baseline correction

References
----------
- Eilers, P. H. C. & Boelens, H. F. M. (2005).
  "Baseline Correction with Asymmetric Least Squares Smoothing".
  Leiden University Medical Centre Report.
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


def estimate_baseline_degree(x: np.ndarray, y: np.ndarray) -> int:
    """
    Suggest polynomial degree based on data characteristics.

    This is a heuristic for interactive use.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber or wavelength array.
    y : np.ndarray
        Intensity array.

    Returns
    -------
    suggested_degree : int
        Suggested polynomial degree (1-10).

    Notes
    -----
    Heuristic:
    - If Y range is < 20% of max(Y): degree 1-2 (flat baseline)
    - If Y is monotonic: degree 1-2 (linear baseline)
    - Otherwise: degree 3 (default for curved baselines)
    """
    if len(y) < 10:
        return 1

    # Check if baseline is relatively flat
    y_range = y.max() - y.min()
    y_max = y.max()

    if y_max > 0 and y_range / y_max < 0.2:
        # Flat baseline
        return 1

    # Check monotonicity (simple heuristic: >80% of points have same sign derivative)
    dy = np.diff(y)
    if np.sum(dy > 0) > 0.8 * len(dy) or np.sum(dy < 0) > 0.8 * len(dy):
        # Monotonic → linear baseline
        return 2

    # Default: curved baseline
    return 3
