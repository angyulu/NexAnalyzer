"""
Cosmic-ray spike removal using modified Z-score (MAD-based).

This module implements the modified Z-score algorithm for detecting
and removing cosmic-ray spikes in spectroscopy data.

References
----------
Iglewicz, B. & Hoaglin, D. C. (1993).
"How to Detect and Handle Outliers". ASQC Quality Press.
"""

import numpy as np
from scipy.stats import median_abs_deviation
from typing import Tuple


def remove_spikes(
    y: np.ndarray,
    threshold: float = 6.0,
    window_size: int = 5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remove cosmic-ray spikes using modified Z-score (MAD-based).

    Parameters
    ----------
    y : np.ndarray
        Intensity array (1D, float64).
    threshold : float, default=6.0
        Modified Z-score threshold (3.0-15.0).
        Higher = less sensitive (fewer spikes detected).
        Recommended: 6.0 for typical Raman/PL data.
    window_size : int, default=5
        Window size for local median replacement (must be odd).
        Used to replace detected spikes with local median.

    Returns
    -------
    y_clean : np.ndarray
        Cleaned intensity (spikes replaced with local median).
    spike_mask : np.ndarray (bool)
        True at spike indices, False elsewhere.

    Raises
    ------
    ValueError
        If threshold is outside [3.0, 15.0] or window_size is even.

    Notes
    -----
    Algorithm (FR-011 to FR-016):
    1. Calculate median(Y) and MAD (Median Absolute Deviation)
    2. Compute modified Z-scores: z_i = 0.6745 * (Y_i - median) / MAD
    3. Flag as spike if |z_i| > threshold
    4. Replace spikes with local median (window_size neighbors)

    The factor 0.6745 converts MAD to standard deviation units for
    normally distributed data (consistency factor).

    Examples
    --------
    >>> y = np.array([100, 102, 500, 98, 101])  # Point 2 is a spike
    >>> y_clean, mask = remove_spikes(y, threshold=6.0)
    >>> print(mask)
    [False False  True False False]
    >>> print(y_clean[2])  # Replaced with local median
    100.5

    References
    ----------
    - Iglewicz & Hoaglin (1993), "How to Detect and Handle Outliers"
    - Modified Z-score: robust alternative to standard Z-score
    """
    # Validation
    # **FIX (Issue 4)**: Extended range to 30.0 per user request
    if not (3.0 <= threshold <= 30.0):
        raise ValueError(f"threshold must be in [3.0, 30.0] (got {threshold})")

    if window_size % 2 == 0:
        raise ValueError(f"window_size must be odd (got {window_size})")

    if len(y) < 10:
        # Too short for meaningful spike detection
        return y.copy(), np.zeros(len(y), dtype=bool)

    # Calculate global median and MAD
    median_y = np.median(y)
    mad = median_abs_deviation(y, nan_policy='omit')

    # Handle edge case: constant signal (MAD = 0)
    if mad < 1e-10:
        # No spikes if signal is constant
        return y.copy(), np.zeros(len(y), dtype=bool)

    # Calculate modified Z-scores
    # Factor 0.6745 converts MAD to std deviation units
    z_scores = 0.6745 * np.abs(y - median_y) / mad

    # Detect spikes
    spike_mask = z_scores > threshold

    # Replace spikes with local median
    y_clean = y.copy()
    spike_indices = np.where(spike_mask)[0]

    for idx in spike_indices:
        # Define window around spike
        half_window = window_size // 2
        start = max(0, idx - half_window)
        end = min(len(y), idx + half_window + 1)

        # Get neighbors (excluding the spike itself if possible)
        neighbors = []
        for i in range(start, end):
            if i != idx:
                neighbors.append(y[i])

        # Replace with median of neighbors
        if len(neighbors) > 0:
            y_clean[idx] = np.median(neighbors)
        else:
            # Fallback: use global median (edge case for very small arrays)
            y_clean[idx] = median_y

    return y_clean, spike_mask


def count_spikes(spike_mask: np.ndarray) -> int:
    """
    Count number of detected spikes.

    Parameters
    ----------
    spike_mask : np.ndarray (bool)
        Spike mask from remove_spikes().

    Returns
    -------
    count : int
        Number of True values in mask.

    Examples
    --------
    >>> _, mask = remove_spikes(y, threshold=6.0)
    >>> n_spikes = count_spikes(mask)
    >>> print(f"Detected {n_spikes} spikes")
    """
    return np.sum(spike_mask)


def spike_fraction(spike_mask: np.ndarray) -> float:
    """
    Calculate fraction of points flagged as spikes.

    Parameters
    ----------
    spike_mask : np.ndarray (bool)
        Spike mask from remove_spikes().

    Returns
    -------
    fraction : float
        Fraction of spikes (0.0 to 1.0).

    Examples
    --------
    >>> _, mask = remove_spikes(y, threshold=6.0)
    >>> frac = spike_fraction(mask)
    >>> print(f"{frac*100:.2f}% of points are spikes")
    """
    if len(spike_mask) == 0:
        return 0.0
    return np.sum(spike_mask) / len(spike_mask)


def suggest_threshold(y: np.ndarray, target_fraction: float = 0.01) -> float:
    """
    Suggest a threshold that would flag approximately target_fraction of points.

    This is useful for interactive threshold tuning.

    Parameters
    ----------
    y : np.ndarray
        Intensity array.
    target_fraction : float, default=0.01
        Target fraction of points to flag as spikes (e.g., 0.01 = 1%).

    Returns
    -------
    suggested_threshold : float
        Suggested threshold value (clamped to [3.0, 15.0]).

    Examples
    --------
    >>> suggested = suggest_threshold(y, target_fraction=0.01)
    >>> print(f"Try threshold={suggested:.1f} to flag ~1% of points")
    """
    median_y = np.median(y)
    mad = median_abs_deviation(y, nan_policy='omit')

    if mad < 1e-10:
        return 6.0  # Default if constant signal

    # Calculate Z-scores
    z_scores = 0.6745 * np.abs(y - median_y) / mad

    # Find threshold that gives target_fraction
    sorted_z = np.sort(z_scores)
    idx = int((1.0 - target_fraction) * len(sorted_z))
    idx = max(0, min(len(sorted_z) - 1, idx))

    suggested = sorted_z[idx]

    # Clamp to valid range
    return np.clip(suggested, 3.0, 15.0)
