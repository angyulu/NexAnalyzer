"""
Preprocessing-state fingerprinting for stale-fit detection.

Moved out of src.ui.control_panel (where it originated) because it is pure
processing-adjacent logic with no Streamlit/UI dependency, while
modules.spectra.processing.auto_workflow needs it and previously had to reach into the
UI layer to get it — a layering violation. Neither function touches
Streamlit; both operate only on the SpectrumFile passed in.
"""

import hashlib


def compute_preprocessing_hash(spectrum) -> str:
    """
    Compute SHA256 hash of preprocessing parameters for stale fit detection.

    This function creates a unique fingerprint of the current preprocessing state
    (despike threshold, baseline algorithm/params). If this hash changes after
    fitting, we know the fit is now "stale" (doesn't match current data).

    Parameters
    ----------
    spectrum : SpectrumFile
        Current spectrum file containing processing settings.

    Returns
    -------
    hash_str : str
        SHA256 hash (64 hexadecimal characters) representing preprocessing state.

    Notes
    -----
    - We only hash PREPROCESSING params (despike, baseline), not peak table
    - Peak table changes don't make fit stale (user can refit with same data)
    - X-range changes reset fit entirely (no need for stale detection)
    """
    # Get processing settings object from spectrum
    settings = spectrum.processing_settings

    # Build parameter string: concatenate all preprocessing params with underscores.
    # WHY THESE PARAMS: They directly affect processed_data.Y (the data we fit to).
    # If any of these change and we rerun processing, Y values change -> fit is stale.
    params_str = f"{settings.despike_threshold}_{settings.despike_applied}_" \
                 f"{settings.baseline_algorithm}_{settings.baseline_degree}_" \
                 f"{settings.baseline_lambda}_{settings.baseline_p}_{settings.baseline_applied}"

    return hashlib.sha256(params_str.encode()).hexdigest()


def mark_fit_stale_if_needed(spectrum):
    """
    Mark existing fit as stale if preprocessing parameters changed.

    This function is called AFTER any preprocessing operation (despike or baseline).
    It checks if the operation changed the preprocessing state, and if so, marks
    any existing fit as "stale" (no longer valid for current data).

    Parameters
    ----------
    spectrum : SpectrumFile
        Current spectrum file (modified in-place).

    Notes
    -----
    - Only marks fit as stale, doesn't delete it (user can still export old fit)
    - User must explicitly refit to clear stale flag
    - Refitting updates last_preprocessing_hash to current state
    """
    if not spectrum.fit_done:
        # No fit exists yet, nothing to mark stale.
        return

    current_hash = compute_preprocessing_hash(spectrum)

    # last_preprocessing_hash is set after a successful fit (peak_fit section).
    # If hashes differ, preprocessing changed since that fit, so it's stale.
    if spectrum.last_preprocessing_hash and current_hash != spectrum.last_preprocessing_hash:
        spectrum.fit_stale = True
