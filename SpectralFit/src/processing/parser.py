"""
Parser for two-column .txt spectrum files.

This module provides functions to:
- Parse two-column .txt files (X, Y) with auto-delimiter detection
- Validate loaded data
- Convert to SpectrumData objects
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Literal
from ..models.spectrum import SpectrumData


def parse_spectrum(filepath: str) -> SpectrumData:
    """
    Parse two-column .txt spectrum file.

    Parameters
    ----------
    filepath : str
        Path to .txt file (two columns: X, Y).

    Returns
    -------
    SpectrumData
        Parsed and validated spectrum data.

    Raises
    ------
    ValueError
        If file cannot be parsed or validation fails.
    FileNotFoundError
        If file does not exist.

    Notes
    -----
    File format requirements (FR-001 to FR-004):
    - Two columns: X (wavenumber or wavelength), Y (intensity)
    - Delimiter: Tab or comma (auto-detected)
    - No header row
    - Numeric values only
    - Y values must be non-negative

    Examples
    --------
    >>> data = parse_spectrum("sample_raman.txt")
    >>> print(data.X.shape, data.Y.shape)
    (1000,) (1000,)
    """
    try:
        # Try to auto-detect delimiter using pandas
        # Try tab first (most common for scientific data)
        try:
            df = pd.read_csv(filepath, sep='\t', header=None, engine='python')
            if df.shape[1] != 2:
                # If not 2 columns, try comma
                df = pd.read_csv(filepath, sep=',', header=None, engine='python')
        except Exception:
            # If tab fails, try comma
            df = pd.read_csv(filepath, sep=',', header=None, engine='python')

        # Validate column count
        if df.shape[1] != 2:
            raise ValueError(
                f"File must have exactly 2 columns (got {df.shape[1]}). "
                f"Expected format: X<delimiter>Y with tab or comma delimiter."
            )

        # Extract X and Y
        X = df.iloc[:, 0].values
        Y = df.iloc[:, 1].values

        # Convert to float64
        try:
            X = X.astype(np.float64)
            Y = Y.astype(np.float64)
        except ValueError as e:
            raise ValueError(
                f"Failed to convert columns to numeric values: {e}. "
                f"Ensure file contains only numeric data with no header row."
            )

        # Create SpectrumData (validation happens in __post_init__)
        return SpectrumData(X=X, Y=Y)

    except FileNotFoundError:
        raise FileNotFoundError(f"Spectrum file not found: {filepath}")

    except pd.errors.EmptyDataError:
        raise ValueError(f"File is empty: {filepath}")

    except Exception as e:
        raise ValueError(
            f"Failed to parse spectrum file '{filepath}': {e}. "
            f"Ensure file is two-column format (X<tab|comma>Y) with no header."
        )


def validate_spectrum_file(filepath: str) -> Tuple[bool, str]:
    """
    Validate .txt spectrum file without loading it.

    Parameters
    ----------
    filepath : str
        Path to .txt file.

    Returns
    -------
    is_valid : bool
        True if file is valid.
    message : str
        Empty if valid, else error message.

    Examples
    --------
    >>> is_valid, msg = validate_spectrum_file("sample.txt")
    >>> if not is_valid:
    ...     print(f"Validation failed: {msg}")
    """
    try:
        parse_spectrum(filepath)
        return True, ""
    except Exception as e:
        return False, str(e)


def detect_negative_x(X: np.ndarray) -> bool:
    """
    Check if X array contains negative values.

    This is expected for Raman spectra with negative shifts
    (Edge Case #1 in spec.md).

    Parameters
    ----------
    X : np.ndarray
        X array to check.

    Returns
    -------
    has_negative : bool
        True if any X values are negative.
    """
    return np.any(X < 0)


def estimate_spectral_resolution(X: np.ndarray) -> float:
    """
    Estimate spectral resolution (median step size).

    Used for auto-calculating width_min in peak fitting bounds.

    Parameters
    ----------
    X : np.ndarray
        X array (wavenumber or wavelength).

    Returns
    -------
    resolution : float
        Median step size in X units.

    Examples
    --------
    >>> X = np.linspace(100, 1000, 1000)
    >>> resolution = estimate_spectral_resolution(X)
    >>> print(f"{resolution:.3f} cm⁻¹")
    0.900 cm⁻¹
    """
    if len(X) < 2:
        return 1.0  # Fallback for single-point spectra (should not happen)

    # Calculate step sizes
    steps = np.diff(X)

    # Use median to be robust to irregular spacing
    resolution = np.median(np.abs(steps))

    return resolution


def detect_mode_from_filename(filename: str) -> Optional[Literal["Raman", "PL"]]:
    """
    Auto-detect spectroscopy mode from filename prefix.

    v2.1+ (FR-12): Automatic mode detection based on naming conventions.

    Parameters
    ----------
    filename : str
        File name (with or without path).

    Returns
    -------
    mode : Optional[Literal["Raman", "PL"]]
        "Raman" if filename starts with "RM" (case-insensitive)
        "PL" if filename starts with "PL" (case-insensitive)
        None if no match (manual mode selection required)

    Notes
    -----
    Detection Rules (FR-12):
    - RM* → Raman mode (e.g., RM_sample.txt, rm_carbon_001.txt)
    - PL* → PL mode (e.g., PL_emission.txt, pl_test.txt)
    - Other patterns → None (no auto-detection)

    Case-insensitive matching ensures compatibility with various naming conventions.

    Examples
    --------
    >>> detect_mode_from_filename("RM_carbon_sample.txt")
    'Raman'
    >>> detect_mode_from_filename("pl_emission_test.txt")
    'PL'
    >>> detect_mode_from_filename("sample_001.txt")
    None
    >>> detect_mode_from_filename("/path/to/RM_data.txt")
    'Raman'
    """
    # Extract basename (remove path if present)
    import os
    basename = os.path.basename(filename)

    # Convert to uppercase for case-insensitive matching
    basename_upper = basename.upper()

    # Check for RM prefix (Raman)
    if basename_upper.startswith("RM"):
        return "Raman"

    # Check for PL prefix (Photoluminescence)
    if basename_upper.startswith("PL"):
        return "PL"

    # No match
    return None
