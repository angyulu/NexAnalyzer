"""
Right panel UI component with FULL processing controls integrated.

v2.2: Migrated from tab modules into accordion sections.
"""

import streamlit as st
import numpy as np
import hashlib
from typing import Optional
from .session_state import get_current_spectrum
from ..processing.despiking import remove_spikes, count_spikes
from ..processing.baseline import (
    baseline_polynomial_with_autoshift,
    baseline_als_with_autoshift
)
from ..models.spectrum import SpectrumData


def validate_peak_row(row, x_range, spectral_resolution):
    """
    Validate a single peak table row.

    Parameters
    ----------
    row : pd.Series
        DataFrame row representing a peak.
    x_range : tuple[float, float]
        (min, max) of X data range.
    spectral_resolution : float
        Median step size in X.

    Returns
    -------
    errors : list[str]
        List of validation error messages.
    """
    import re
    errors = []

    # **FIX (Issue 2)**: Guard against None values in new/incomplete rows
    # When user adds row via data_editor "+", all fields are None initially
    # Skip validation for incomplete rows (return empty errors)
    required_fields = ["Label", "Center", "Amplitude", "FWHM", "Shape", "Color"]
    if any(row[field] is None for field in required_fields):
        return []

    # Center validation
    if not (x_range[0] <= row["Center"] <= x_range[1]):
        errors.append(
            f"Peak '{row['Label']}': Center {row['Center']:.2f} outside data range "
            f"[{x_range[0]:.2f}, {x_range[1]:.2f}]"
        )

    # Amplitude validation
    if row["Amplitude"] <= 0:
        errors.append(f"Peak '{row['Label']}': Amplitude must be > 0 (got {row['Amplitude']:.2f})")

    # FWHM validation
    if row["FWHM"] <= 0:
        errors.append(f"Peak '{row['Label']}': FWHM must be > 0 (got {row['FWHM']:.2f})")

    x_span = x_range[1] - x_range[0]
    if row["FWHM"] > 0.5 * x_span:
        errors.append(
            f"Peak '{row['Label']}': FWHM {row['FWHM']:.2f} > 50% of data range ({0.5*x_span:.2f})"
        )

    if row["FWHM"] < spectral_resolution:
        errors.append(
            f"Peak '{row['Label']}': FWHM {row['FWHM']:.2f} < spectral resolution ({spectral_resolution:.2f})"
        )

    # Shape validation
    if not (0.0 <= row["Shape"] <= 1.0):
        errors.append(f"Peak '{row['Label']}': Shape must be in [0.0, 1.0] (got {row['Shape']:.2f})")

    # Label validation
    if len(row["Label"]) > 50:
        errors.append(f"Peak '{row['Label']}': Label too long (max 50 characters)")

    # Color validation (basic hex check)
    if not re.match(r'^#[0-9A-Fa-f]{6}$', row["Color"]):
        errors.append(f"Peak '{row['Label']}': Invalid color '{row['Color']}' (must be #RRGGBB)")

    return errors


def compute_preprocessing_hash(spectrum) -> str:
    """
    Compute SHA256 hash of preprocessing parameters for stale fit detection.

    Parameters
    ----------
    spectrum : SpectrumFile
        Current spectrum file.

    Returns
    -------
    str
        SHA256 hash of (despike + baseline parameters).
    """
    settings = spectrum.processing_settings
    params_str = f"{settings.despike_threshold}_{settings.despike_applied}_" \
                 f"{settings.baseline_algorithm}_{settings.baseline_degree}_" \
                 f"{settings.baseline_lambda}_{settings.baseline_p}_{settings.baseline_applied}"
    return hashlib.sha256(params_str.encode()).hexdigest()


def mark_fit_stale_if_needed(spectrum):
    """Mark existing fit as stale if preprocessing params changed."""
    if spectrum.fit_done:
        current_hash = compute_preprocessing_hash(spectrum)
        if spectrum.last_preprocessing_hash and current_hash != spectrum.last_preprocessing_hash:
            spectrum.fit_stale = True


def is_section_enabled(section_id: str, spectrum: Optional[object]) -> bool:
    """Check if a processing section is enabled based on workflow dependencies."""
    if spectrum is None:
        return section_id in ["processing_range", "despike", "baseline", "export"]

    if section_id == "peak_fit":
        baseline_done = getattr(spectrum, 'baseline_done', False)
        return baseline_done

    return True


def render_view_options():
    """Render plot layer visibility checkboxes."""
    with st.expander("🔍 View Options", expanded=False):
        st.markdown("**Plot Layer Visibility**")

        # Simplified view options per user request:
        # - Removed "Show Baseline-corrected" (automatically managed by processing stages)
        # - Keep only essential checkboxes for user control
        st.checkbox("Show Raw", value=True, key="show_raw",
                   help="Show raw data (before any processing)")
        st.checkbox("Show De-spiked", value=False, key="show_despiked",
                   help="Show data after spike removal")
        st.checkbox("Show Baseline-corrected", value=False, key="show_corrected",
                   help="Show data after baseline correction")

        st.markdown("---")
        st.markdown("**Peak Fitting Display**")
        st.checkbox("Show Fit", value=False, key="show_fit",
                   help="Show total fitted curve")
        st.checkbox("Show Components", value=False, key="show_components",
                   help="Show individual peak components")

        st.caption("Toggle plot layers on/off without reprocessing.")


def render_processing_range_section(is_expanded: bool):
    """Render Processing Range section with X-range controls."""
    spectrum = get_current_spectrum()

    with st.expander("1️⃣ Processing Range", expanded=is_expanded):
        if spectrum is None:
            st.info("Load a file to configure processing range")
            return

        st.markdown("**X-Range Limiting** (v2.1+)")
        st.caption("Process only a specific region of the spectrum")

        # Get data range from RAW data (not processed, to allow resetting)
        X_raw = spectrum.raw_data.X
        x_min_data, x_max_data = float(X_raw.min()), float(X_raw.max())

        # Checkbox to enable
        x_range_enabled = st.checkbox(
            "Enable X-range limiting",
            value=spectrum.x_range_enabled,
            help="Process only a specific region"
        )

        # Numeric inputs
        col1, col2 = st.columns(2)
        with col1:
            x_min = st.number_input(
                f"X min ({spectrum.mode} units)",
                value=spectrum.x_min if spectrum.x_min is not None else x_min_data,
                min_value=x_min_data,
                max_value=x_max_data,
                disabled=not x_range_enabled
            )
        with col2:
            x_max = st.number_input(
                f"X max ({spectrum.mode} units)",
                value=spectrum.x_max if spectrum.x_max is not None else x_max_data,
                min_value=x_min_data,
                max_value=x_max_data,
                disabled=not x_range_enabled
            )

        # Validate
        if x_range_enabled and x_min >= x_max:
            st.error("X min must be less than X max")
            return

        # Apply X-range button
        if st.button("🚀 Apply X-Range", key="apply_xrange", disabled=not x_range_enabled):
            try:
                # Crop the data to selected range
                X_raw = spectrum.raw_data.X
                Y_raw = spectrum.raw_data.Y

                # Find indices within range
                mask = (X_raw >= x_min) & (X_raw <= x_max)

                if not np.any(mask):
                    st.error(f"No data points in range [{x_min:.1f}, {x_max:.1f}]")
                    return

                # Crop the data
                X_cropped = X_raw[mask]
                Y_cropped = Y_raw[mask]

                # Update both raw and processed data
                spectrum.raw_data = SpectrumData(X=X_cropped, Y=Y_cropped)
                spectrum.processed_data = SpectrumData(X=X_cropped, Y=Y_cropped)

                # Reset range settings (data is now cropped, so disable limiting)
                spectrum.x_range_enabled = False
                spectrum.x_min = None
                spectrum.x_max = None

                # Reset processing flags since we have new data range
                spectrum.despike_done = False
                spectrum.baseline_done = False
                spectrum.fit_done = False
                spectrum.processing_settings.despike_applied = False
                spectrum.processing_settings.baseline_applied = False

                actual_min = float(X_cropped.min())
                actual_max = float(X_cropped.max())
                st.success(f"✅ Data cropped to: {actual_min:.1f} - {actual_max:.1f} ({len(X_cropped)} points)")

                # Auto-expand next section
                st.session_state['expanded_section'] = 'despike'
                # **FIX (Issue 3)**: Reset view options to show only raw
                st.session_state['show_raw'] = True
                st.session_state['show_despiked'] = False
                st.session_state['show_corrected'] = False
                st.session_state['show_fit'] = False
                st.session_state['show_components'] = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ X-range application failed: {e}")

        # Show current status - check if original data range differs from full data
        # (This would require storing original full range, for now just show current range)
        n_points = len(spectrum.raw_data.X)
        current_min = float(spectrum.raw_data.X.min())
        current_max = float(spectrum.raw_data.X.max())
        st.caption(f"Current data range: {current_min:.1f} - {current_max:.1f} ({n_points} points)")


def render_despike_section(is_expanded: bool):
    """Render De-spiking section with controls and Run button."""
    spectrum = get_current_spectrum()

    with st.expander("2️⃣ De-spiking", expanded=is_expanded):
        if spectrum is None:
            st.info("Load a file to configure de-spiking")
            return

        st.markdown("**Remove Cosmic-Ray Spikes**")
        st.caption("Modified Z-score algorithm (MAD-based)")

        # Enable real-time preview toggle
        show_preview = st.checkbox(
            "Show Real-Time Preview",
            value=True,
            help="Preview spike detection as you adjust threshold",
            key="despike_preview_toggle"
        )

        # **FIX (Issue 4)**: Extended max_value to 30.0 per user request
        threshold = st.slider(
            "Sensitivity Threshold",
            min_value=3.0,
            max_value=30.0,
            value=spectrum.processing_settings.despike_threshold,
            step=0.5,
            help="Higher = less sensitive (fewer spikes detected)\nDefault: 6.0\n⚠️ Values >15 may miss real spikes"
        )

        # Real-time preview computation
        if show_preview:
            try:
                y_clean_preview, spike_mask = remove_spikes(
                    spectrum.processed_data.Y,
                    threshold=threshold
                )

                # Store preview in session state for unified_plot to render
                st.session_state['despike_preview'] = {
                    'x': spectrum.processed_data.X,
                    'despiked': y_clean_preview
                }

                n_spikes = count_spikes(spike_mask)
                frac = n_spikes / len(spike_mask) * 100
                st.caption(f"✓ Preview: {n_spikes} spikes detected ({frac:.2f}% of points)")

            except Exception as e:
                st.warning(f"Preview failed: {e}")
                st.session_state['despike_preview'] = None
        else:
            # Clear preview if disabled
            st.session_state['despike_preview'] = None

        if st.button("🚀 Run Despike", key="run_despike"):
            try:
                # Update threshold
                spectrum.processing_settings.despike_threshold = threshold

                # Run de-spiking
                y_clean, spike_mask = remove_spikes(
                    spectrum.processed_data.Y,
                    threshold=threshold
                )

                # Update processed data
                spectrum.processed_data = SpectrumData(
                    X=spectrum.processed_data.X,
                    Y=y_clean
                )

                # Mark as applied
                spectrum.processing_settings.despike_applied = True
                spectrum.despike_done = True

                # Check if fit needs to be marked stale
                mark_fit_stale_if_needed(spectrum)

                # Clear despike preview from session state
                if 'despike_preview' in st.session_state:
                    st.session_state['despike_preview'] = None

                # Report results
                n_spikes = count_spikes(spike_mask)
                frac = n_spikes / len(spike_mask) * 100
                st.success(f"✅ Removed {n_spikes} spikes ({frac:.2f}% of points)")

                # Auto-expand next section
                st.session_state['expanded_section'] = 'baseline'
                # **FIX (Issue 3 UPDATE)**: Show Raw AND De-spiked for comparison
                st.session_state['show_raw'] = True
                st.session_state['show_despiked'] = True
                st.session_state['show_corrected'] = False
                st.session_state['show_fit'] = False
                st.session_state['show_components'] = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ Spike removal failed: {e}")

        if spectrum.despike_done:
            st.caption("✓ De-spiking completed")


def render_baseline_section(is_expanded: bool):
    """Render Baseline Correction section with real-time preview."""
    spectrum = get_current_spectrum()

    with st.expander("3️⃣ Baseline Correction", expanded=is_expanded):
        if spectrum is None:
            st.info("Load a file to configure baseline correction")
            return

        st.markdown("**Baseline Correction**")
        st.caption("Subtract fluorescence background")

        baseline_alg = st.radio(
            "Algorithm",
            ["Polynomial", "ALS", "Rolling Ball", "Spline", "airPLS"],
            index={
                "Polynomial": 0,
                "ALS": 1,
                "Rolling Ball": 2,
                "Spline": 3,
                "airPLS": 4
            }.get(spectrum.processing_settings.baseline_algorithm, 0),
            help=(
                "Polynomial: Fast, simple (degree 2-3)\n"
                "ALS: Good for fluorescence (tune λ and p)\n"
                "Rolling Ball: Excellent for many sharp peaks\n"
                "Spline: Local control, no oscillations\n"
                "airPLS: Self-optimizing ALS (advanced)"
            )
        )

        # Enable real-time preview toggle
        show_preview = st.checkbox(
            "Show Real-Time Preview",
            value=True,
            help="Update plot preview as you adjust parameters"
        )

        if baseline_alg == "Polynomial":
            # Auto-suggest polynomial degree based on data
            from ..processing.baseline import estimate_baseline_degree
            X = spectrum.processed_data.X
            Y = spectrum.processed_data.Y
            suggested_degree = estimate_baseline_degree(X, Y)
            st.caption(f"💡 Suggested degree based on data: {suggested_degree}")

            degree = st.slider(
                "Polynomial Degree",
                min_value=1,
                max_value=10,
                value=spectrum.processing_settings.baseline_degree,
                help="Controls baseline flexibility. Recommended: 2-3 for simple, 4-5 for complex."
            )

            # Warning for high degrees
            if degree > 6:
                st.warning(
                    f"⚠️ Degree {degree} may cause oscillations (Runge's phenomenon). "
                    f"Consider using ALS instead for complex baselines."
                )
            elif degree > 3:
                st.info(
                    f"ℹ️ Degree {degree} is flexible. Check preview to ensure baseline doesn't fit through peaks."
                )

            lambda_val = None
            p_val = None

        elif baseline_alg == "ALS":
            degree = None

            # Log-scale slider for lambda (easier to tune across wide range)
            import numpy as np
            lambda_log = st.slider(
                "Smoothness (log₁₀ λ)",
                min_value=3.0,   # 10^3 = 1,000
                max_value=6.0,   # 10^6 = 1,000,000
                value=np.log10(max(spectrum.processing_settings.baseline_lambda, 10000.0)),
                step=0.1,
                format="%.1f",
                help=(
                    "Controls baseline smoothness on log scale.\n"
                    "• 3.0 (1k): Very flexible, follows data closely\n"
                    "• 4.0 (10k): Typical for Raman\n"
                    "• 5.0 (100k): Smooth, good for fluorescence\n"
                    "• 6.0 (1M): Very smooth"
                )
            )
            lambda_val = 10 ** lambda_log
            st.caption(f"Actual λ = {lambda_val:,.0f}")

            # Rephrased asymmetry parameter for better user understanding
            p_val = st.slider(
                "Peak Avoidance",
                min_value=0.001,
                max_value=0.01,
                value=min(spectrum.processing_settings.baseline_p, 0.001),
                step=0.001,
                format="%.3f",
                help=(
                    "Controls how strongly the baseline avoids peaks.\n"
                    "• 0.001: Very strong avoidance (ignores peaks completely)\n"
                    "• 0.005: Moderate avoidance (typical for complex spectra)\n"
                    "• 0.01: Gentle avoidance (may fit through small peaks)"
                )
            )
            st.caption(f"Technical: p={p_val:.4f}, weight ratio = 1:{int((1-p_val)/p_val)}")

        elif baseline_alg == "Rolling Ball":
            degree = None
            lambda_val = None
            p_val = None

            # Rolling ball radius parameter
            radius = st.slider(
                "Ball Radius",
                min_value=10.0,
                max_value=200.0,
                value=50.0,
                step=5.0,
                help=(
                    "Radius of the rolling ball in X units (cm⁻¹ or nm).\n"
                    "Larger radius = smoother baseline.\n"
                    "• 20-50: For narrow peaks\n"
                    "• 50-100: General purpose\n"
                    "• 100-200: For broad features"
                )
            )

        elif baseline_alg == "Spline":
            degree = None
            lambda_val = None
            p_val = None

            # Spline smoothness parameter
            smoothness_auto = st.checkbox(
                "Auto-calculate smoothness",
                value=True,
                help="Automatically calculate smoothness based on data variance"
            )

            if smoothness_auto:
                smoothness = None
                st.caption("Using automatic smoothness = len(X) × var(Y)")
            else:
                smoothness = st.slider(
                    "Smoothness Factor",
                    min_value=100.0,
                    max_value=100000.0,
                    value=10000.0,
                    step=1000.0,
                    format="%.0f",
                    help=(
                        "Spline smoothing factor (s parameter).\n"
                        "Larger = smoother baseline.\n"
                        "• 100-1000: Flexible spline\n"
                        "• 1000-10000: Balanced\n"
                        "• 10000+: Very smooth"
                    )
                )

        elif baseline_alg == "airPLS":
            degree = None
            p_val = None

            # airPLS lambda parameter (similar to ALS)
            import numpy as np
            lambda_log = st.slider(
                "Smoothness (log₁₀ λ)",
                min_value=3.0,   # 10^3
                max_value=7.0,   # 10^7
                value=5.0,       # 10^5 = 100,000
                step=0.1,
                format="%.1f",
                help=(
                    "Controls baseline smoothness (automatic peak avoidance).\n"
                    "• 3.0 (1k): Very flexible\n"
                    "• 5.0 (100k): Balanced (recommended)\n"
                    "• 7.0 (10M): Very smooth"
                )
            )
            lambda_val = 10 ** lambda_log
            st.caption(f"Actual λ = {lambda_val:,.0f}")
            st.info("ℹ️ airPLS automatically optimizes peak avoidance (no manual p tuning needed)")

        else:  # Fallback for any future algorithms
            degree = None
            lambda_val = None
            p_val = None

        # Peak Exclusion Regions (optional)
        st.markdown("---")
        st.markdown("**Peak Exclusion Regions** (optional)")
        st.caption("Define X ranges to exclude from baseline fitting (e.g., known peak locations)")

        exclude_regions_text = st.text_area(
            "Exclusion Ranges",
            value="",
            placeholder="Example: 1300-1400, 1550-1620 (comma-separated)",
            help="Enter X ranges to exclude. Baseline will interpolate through these regions.",
            key="baseline_exclusions"
        )

        # Parse exclusion regions
        exclusions = []
        if exclude_regions_text.strip():
            for region in exclude_regions_text.split(','):
                try:
                    parts = region.strip().split('-')
                    if len(parts) == 2:
                        x_min = float(parts[0].strip())
                        x_max = float(parts[1].strip())
                        if x_min < x_max:
                            exclusions.append((x_min, x_max))
                        else:
                            st.error(f"Invalid region: {region}. Min must be < Max.")
                    else:
                        st.error(f"Invalid format: {region}. Use 'min-max' format.")
                except ValueError:
                    st.error(f"Invalid numbers in region: {region}")

        if exclusions:
            st.success(f"✓ {len(exclusions)} exclusion region(s) defined")

        # Real-time preview computation
        if show_preview:
            try:
                from ..processing.baseline import (
                    baseline_polynomial_with_mask, baseline_als_with_mask,
                    baseline_rolling_ball, baseline_spline, baseline_airpls
                )

                X = spectrum.processed_data.X
                Y = spectrum.processed_data.Y

                if baseline_alg == "Polynomial":
                    if exclusions:
                        y_corrected_preview, baseline_preview = baseline_polynomial_with_mask(
                            X, Y, degree=degree, exclusions=exclusions
                        )
                        y_shift = 0.0
                    else:
                        y_corrected_preview, baseline_preview, y_shift = baseline_polynomial_with_autoshift(
                            X, Y, degree=degree
                        )

                elif baseline_alg == "ALS":
                    if exclusions:
                        y_corrected_preview, baseline_preview = baseline_als_with_mask(
                            X, Y, lambda_=lambda_val, p=p_val, exclusions=exclusions
                        )
                        y_shift = 0.0
                    else:
                        y_corrected_preview, baseline_preview, y_shift = baseline_als_with_autoshift(
                            X, Y, lambda_=lambda_val, p=p_val
                        )

                elif baseline_alg == "Rolling Ball":
                    y_corrected_preview, baseline_preview = baseline_rolling_ball(X, Y, radius=radius)
                    y_shift = 0.0

                elif baseline_alg == "Spline":
                    y_corrected_preview, baseline_preview = baseline_spline(X, Y, smoothness=smoothness)
                    y_shift = 0.0

                elif baseline_alg == "airPLS":
                    y_corrected_preview, baseline_preview = baseline_airpls(X, Y, lambda_=lambda_val)
                    y_shift = 0.0

                # Store preview in session state for unified_plot to render
                st.session_state['baseline_preview'] = {
                    'x': X,
                    'baseline': baseline_preview,
                    'corrected': y_corrected_preview
                }

                st.caption(f"✓ Preview active (Y-shift: {y_shift:.1f})")

            except Exception as e:
                st.warning(f"Preview failed: {e}")
                st.session_state['baseline_preview'] = None
        else:
            # Clear preview if disabled
            st.session_state['baseline_preview'] = None

        # Run button
        if st.button("🚀 Run Baseline Correction", key="run_baseline"):
            try:
                from ..processing.baseline import (
                    baseline_polynomial_with_mask, baseline_als_with_mask,
                    baseline_rolling_ball, baseline_spline, baseline_airpls,
                    calculate_baseline_quality_metrics
                )

                # Update settings
                spectrum.processing_settings.baseline_algorithm = baseline_alg
                if baseline_alg == "Polynomial":
                    spectrum.processing_settings.baseline_degree = degree
                elif baseline_alg in ["ALS", "airPLS"]:
                    spectrum.processing_settings.baseline_lambda = lambda_val
                    if baseline_alg == "ALS":
                        spectrum.processing_settings.baseline_p = p_val

                # Run baseline correction
                X = spectrum.processed_data.X
                Y = spectrum.processed_data.Y

                if baseline_alg == "Polynomial":
                    if exclusions:
                        y_corrected, baseline = baseline_polynomial_with_mask(
                            X, Y, degree=degree, exclusions=exclusions
                        )
                        y_shift = 0.0
                    else:
                        y_corrected, baseline, y_shift = baseline_polynomial_with_autoshift(
                            X, Y, degree=degree
                        )

                elif baseline_alg == "ALS":
                    if exclusions:
                        y_corrected, baseline = baseline_als_with_mask(
                            X, Y, lambda_=lambda_val, p=p_val, exclusions=exclusions
                        )
                        y_shift = 0.0
                    else:
                        y_corrected, baseline, y_shift = baseline_als_with_autoshift(
                            X, Y, lambda_=lambda_val, p=p_val
                        )

                elif baseline_alg == "Rolling Ball":
                    y_corrected, baseline = baseline_rolling_ball(X, Y, radius=radius)
                    y_shift = 0.0

                elif baseline_alg == "Spline":
                    y_corrected, baseline = baseline_spline(X, Y, smoothness=smoothness)
                    y_shift = 0.0

                elif baseline_alg == "airPLS":
                    y_corrected, baseline = baseline_airpls(X, Y, lambda_=lambda_val)
                    y_shift = 0.0

                # Update processed data
                spectrum.processed_data = SpectrumData(X=X, Y=y_corrected)
                spectrum.processing_settings.baseline_applied = True
                spectrum.processing_settings.y_shift = y_shift
                spectrum.baseline_done = True

                # Update preprocessing hash
                spectrum.last_preprocessing_hash = compute_preprocessing_hash(spectrum)

                # Check if fit needs to be marked stale
                mark_fit_stale_if_needed(spectrum)

                # Clear baseline preview from session state
                if 'baseline_preview' in st.session_state:
                    st.session_state['baseline_preview'] = None

                # Calculate and display quality metrics
                metrics = calculate_baseline_quality_metrics(Y, baseline, X)

                st.success(f"✅ Baseline corrected (Y-shift: {y_shift:.1f})")

                # Display quality metrics in columns
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Residual Std", f"{metrics['residual_std']:.1f}",
                              help="Lower = better fit (but beware overfitting)")
                with col2:
                    st.metric("Roughness", f"{metrics['roughness']:.2e}",
                              help="Lower = smoother baseline (more desirable)")
                with col3:
                    st.metric("Peaks Found", metrics['peak_count'],
                              help="Number of peaks preserved above baseline")

                # Auto-expand next section
                st.session_state['expanded_section'] = 'peak_fit'
                # **FIX (Issue 3 UPDATE)**: Show De-spiked AND Baseline-corrected for comparison
                # User wants to see despiked (original) + baseline-corrected (result) curves
                st.session_state['show_raw'] = False
                st.session_state['show_despiked'] = True
                st.session_state['show_corrected'] = True
                st.session_state['show_fit'] = False
                st.session_state['show_components'] = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ Baseline correction failed: {e}")

        if spectrum.baseline_done:
            st.caption("✓ Baseline correction completed")


def render_peak_fit_section(is_expanded: bool, is_enabled: bool):
    """Render Peak Fitting section with full Voigt fitting controls."""
    if not is_enabled:
        with st.expander("4️⃣ Peak Fitting", expanded=False):
            st.warning("⚠️ Complete baseline correction first")
            return

    with st.expander("4️⃣ Peak Fitting", expanded=is_expanded):
        spectrum = get_current_spectrum()

        if spectrum is None:
            st.info("Load a file to configure peak fitting")
            return

        if spectrum.fit_stale:
            st.warning("⚠️ Preprocessing changed; fit no longer matches current data. Please refit.")

        st.markdown("**Peak Table**")
        st.caption("Define initial guesses for Voigt peak fitting")

        # Peak table buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 Auto-Find", key="auto_find_peaks", help="Automatically detect peaks"):
                try:
                    from ..processing.fitting import auto_find_peaks
                    peak_table = auto_find_peaks(
                        spectrum.processed_data.X,
                        spectrum.processed_data.Y,
                        mode=spectrum.mode,
                        min_peaks=2,
                        max_peaks=5,
                        prominence_threshold=0.05
                    )
                    spectrum.peak_table = peak_table
                    st.success(f"✅ Found {len(peak_table)} peaks")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Auto-find failed: {e}")

        with col2:
            if st.button("➕ Add Peak", key="add_peak", help="Manually add a peak"):
                from ..models.peak import PeakDefinition
                x_center = (spectrum.processed_data.X.min() + spectrum.processed_data.X.max()) / 2
                y_max = spectrum.processed_data.Y.max()
                dx = (spectrum.processed_data.X.max() - spectrum.processed_data.X.min())

                new_peak = PeakDefinition(
                    center=x_center,
                    amplitude=y_max * 0.5,
                    width_fwhm=dx * 0.05,
                    label=f"Peak {len(spectrum.peak_table) + 1}"
                )
                spectrum.peak_table.append(new_peak)
                st.rerun()

        with col3:
            if len(spectrum.peak_table) > 0:
                if st.button("🗑️ Clear All", key="clear_peaks", help="Remove all peaks"):
                    spectrum.peak_table = []
                    spectrum.fit_result = None
                    spectrum.fit_done = False
                    st.rerun()

        # Display editable peak table
        if len(spectrum.peak_table) == 0:
            st.info("No peaks defined. Click 'Auto-Find' or 'Add Peak' button, or add rows directly in the table below")
        else:
            import pandas as pd
            import numpy as np
            from ..models.peak import PeakDefinition

            # Calculate data properties for bounds and validation
            x_range = (spectrum.processed_data.X.min(), spectrum.processed_data.X.max())
            y_max = spectrum.processed_data.Y.max()
            spectral_resolution = np.median(np.abs(np.diff(spectrum.processed_data.X)))

            # Build DataFrame with editable and display columns
            peak_data = []
            for i, peak in enumerate(spectrum.peak_table):
                # Recalculate bounds for display
                peak.calculate_auto_bounds(spectrum.mode, x_range, y_max, spectral_resolution)

                peak_data.append({
                    "ID": i + 1,
                    "Label": peak.label,
                    "Center": peak.center,
                    "Amplitude": peak.amplitude,
                    "FWHM": peak.width_fwhm,
                    "Shape": peak.shape,
                    "Color": peak.color,
                    "Center Range": f"{peak.center_min:.1f} - {peak.center_max:.1f}",
                    "Width Range": f"{peak.width_min:.1f} - {peak.width_max:.1f}"
                })

            df = pd.DataFrame(peak_data)

            # Editable data editor with column configuration
            x_unit = " (cm⁻¹)" if spectrum.mode == "Raman" else " (nm)"
            edited_df = st.data_editor(
                df,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", disabled=True, help="Peak index"),
                    "Label": st.column_config.TextColumn("Label", max_chars=50, help="Peak name (max 50 characters)"),
                    "Center": st.column_config.NumberColumn(
                        f"Center{x_unit}",
                        format="%.2f",
                        help="Peak position"
                    ),
                    "Amplitude": st.column_config.NumberColumn(
                        "Amp",
                        format="%.0f",
                        help="Peak height (NOT integrated intensity)"
                    ),
                    "FWHM": st.column_config.NumberColumn(
                        "FWHM",
                        format="%.2f",
                        help="Full-width-at-half-maximum"
                    ),
                    "Shape": st.column_config.NumberColumn(
                        "Shape (G→L)",
                        format="%.2f",
                        min_value=0.0,
                        max_value=1.0,
                        help="0=Pure Gaussian, 1=Pure Lorentzian, 0.5=Equal mix"
                    ),
                    "Color": st.column_config.TextColumn("Color", help="Peak color in plot (hex #RRGGBB)"),
                    "Center Range": st.column_config.TextColumn("Center Bounds", disabled=True, help="Auto-calculated fitting bounds"),
                    "Width Range": st.column_config.TextColumn("Width Bounds", disabled=True, help="Auto-calculated fitting bounds")
                },
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",  # Allow add/delete via table
                key="peak_table_editor"
            )

            # Sync edits back to spectrum.peak_table
            validation_errors = []

            # Handle row additions
            if len(edited_df) > len(spectrum.peak_table):
                # Compute smart defaults
                x_center = (x_range[0] + x_range[1]) / 2
                amp_default = y_max * 0.5
                fwhm_default = 10 * spectral_resolution
                default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                                  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

                for idx in range(len(spectrum.peak_table), len(edited_df)):
                    row = edited_df.iloc[idx]

                    # Use row values if provided, else defaults
                    new_peak = PeakDefinition(
                        center=row.get("Center") if pd.notna(row.get("Center")) else x_center,
                        amplitude=row.get("Amplitude") if pd.notna(row.get("Amplitude")) else amp_default,
                        width_fwhm=row.get("FWHM") if pd.notna(row.get("FWHM")) else fwhm_default,
                        label=row.get("Label") if pd.notna(row.get("Label")) else f"Peak {len(spectrum.peak_table) + 1}",
                        shape=row.get("Shape") if pd.notna(row.get("Shape")) else 0.5,
                        color=row.get("Color") if pd.notna(row.get("Color")) else default_colors[len(spectrum.peak_table) % 10]
                    )
                    spectrum.peak_table.append(new_peak)

            # Handle row deletions
            elif len(edited_df) < len(spectrum.peak_table):
                # **FIX (Issue 1)**: Rebuild peak_table using position-based iteration
                new_peak_table = []
                for idx in range(len(edited_df)):
                    row = edited_df.iloc[idx]  # Use iloc for position-based access

                    # Validate row BEFORE adding to peak_table
                    errors = validate_peak_row(row, x_range, spectral_resolution)
                    if errors:
                        validation_errors.extend(errors)
                        # Still add peak (user will see validation errors)

                    peak = PeakDefinition(
                        center=row["Center"],
                        amplitude=row["Amplitude"],
                        width_fwhm=row["FWHM"],
                        label=row["Label"],
                        shape=row["Shape"],
                        color=row["Color"]
                    )
                    new_peak_table.append(peak)

                spectrum.peak_table = new_peak_table

            # **FIX (Issue 1)**: Update existing peaks using position-based iteration
            # Use range(len()) instead of iterrows() to avoid index mismatch
            for idx in range(len(edited_df)):
                row = edited_df.iloc[idx]  # Use iloc for position-based access

                # Validate row
                errors = validate_peak_row(row, x_range, spectral_resolution)
                if errors:
                    validation_errors.extend(errors)
                    continue

                # Ensure peak_table has enough elements (handle edge cases)
                if idx < len(spectrum.peak_table):
                    peak = spectrum.peak_table[idx]
                    peak.center = row["Center"]
                    peak.amplitude = row["Amplitude"]
                    peak.width_fwhm = row["FWHM"]
                    peak.label = row["Label"]
                    peak.shape = row["Shape"]
                    peak.color = row["Color"]

                    # Recalculate bounds after edit
                    peak.calculate_auto_bounds(spectrum.mode, x_range, y_max, spectral_resolution)

            # Display validation errors
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                st.warning("⚠️ Fix validation errors before fitting")

            # Remove individual peak (keep this for now, can remove rows manually)
            if len(spectrum.peak_table) > 1:
                st.markdown("---")
                remove_id = st.selectbox(
                    "Remove peak:",
                    options=list(range(len(spectrum.peak_table))),
                    format_func=lambda i: f"{spectrum.peak_table[i].label} @ {spectrum.peak_table[i].center:.2f}",
                    key="remove_peak_select"
                )
                if st.button("🗑️ Remove Selected", key="remove_peak_btn"):
                    del spectrum.peak_table[remove_id]
                    st.rerun()

        # Run Fitting button
        if len(spectrum.peak_table) > 0:
            st.markdown("---")
            if st.button("🚀 Run Voigt Fit", key="run_fit"):
                if len(spectrum.peak_table) > 10:
                    st.error("❌ Maximum 10 peaks allowed")
                else:
                    try:
                        from ..processing.fitting import fit_voigt_peaks, detect_overlapping_peaks

                        X_fit = spectrum.processed_data.X
                        Y_fit = spectrum.processed_data.Y

                        # Check for overlapping peaks before fitting
                        overlap_warnings = detect_overlapping_peaks(spectrum.peak_table, merge_threshold=2.0)
                        if overlap_warnings:
                            for warning in overlap_warnings:
                                st.warning(warning)

                        with st.spinner("Fitting in progress..."):
                            fit_result = fit_voigt_peaks(
                                X_fit,
                                Y_fit,
                                spectrum.peak_table,
                                mode=spectrum.mode
                            )

                            spectrum.fit_result = fit_result

                            if fit_result.success:
                                # Mark fit as done and update hash
                                spectrum.fit_done = True
                                spectrum.fit_stale = False
                                spectrum.last_preprocessing_hash = compute_preprocessing_hash(spectrum)

                                st.success(
                                    f"✅ Fit converged | R² = {fit_result.r_squared:.4f} | "
                                    f"χ² = {fit_result.chi_squared:.2e} | "
                                    f"Time: {fit_result.convergence_time:.2f}s"
                                )

                                # Auto-expand export section
                                st.session_state['expanded_section'] = 'export'

                                # Clear all preview states
                                if 'despike_preview' in st.session_state:
                                    st.session_state['despike_preview'] = None
                                if 'baseline_preview' in st.session_state:
                                    st.session_state['baseline_preview'] = None

                                # **FIX (Issue 3)**: Show fit results only (no despiked curves)
                                st.session_state['show_raw'] = False
                                st.session_state['show_despiked'] = False
                                st.session_state['show_corrected'] = True
                                st.session_state['show_fit'] = True
                                st.session_state['show_components'] = False
                                st.rerun()
                            else:
                                st.error(f"❌ {fit_result.error_message}")

                    except Exception as e:
                        import traceback
                        # Print full traceback to terminal for debugging
                        print("\n" + "="*80)
                        print("FITTING ERROR - Full Traceback:")
                        print("="*80)
                        traceback.print_exc()
                        print("="*80 + "\n")
                        st.error(f"❌ Fitting failed: {e}")

        # Display fit results if available
        if spectrum.fit_result is not None and spectrum.fit_result.success:
            st.markdown("---")
            st.markdown("**Fit Results**")

            import pandas as pd
            results_data = []
            for peak in spectrum.fit_result.fitted_peaks:
                results_data.append({
                    "Label": peak.label,
                    "Center": f"{peak.center:.2f}",
                    "±": f"{peak.center_stderr:.2f}",
                    "Amp": f"{peak.amplitude:.0f}",
                    "FWHM": f"{peak.width_fwhm:.2f}"
                })

            df_results = pd.DataFrame(results_data)
            st.dataframe(df_results, hide_index=True, use_container_width=True, height=150)

            st.caption(f"✓ R² = {spectrum.fit_result.r_squared:.4f}, χ² = {spectrum.fit_result.chi_squared:.2e}")

        if spectrum.fit_done:
            st.caption("✓ Peak fitting completed")


def render_export_section(is_expanded: bool):
    """Render Export section (placeholder - full implementation in Phase 4.1)."""
    with st.expander("5️⃣ Export", expanded=is_expanded):
        spectrum = get_current_spectrum()

        if spectrum is None:
            st.info("Load and process files to export results")
            return

        st.info("Export controls will be fully integrated in next update")
        st.caption("For now, use the old Export tab if needed")


def render_control_panel():
    """Render the right panel with accordion sections for all processing controls."""
    # Get current file and expanded section state
    spectrum = get_current_spectrum()
    expanded_section = st.session_state.get('expanded_section', 'processing_range')

    # **FIX (Issue 6c)**: Wrap entire panel in scrollable container
    with st.container(height=800):  # Fixed height scrollable container
        # Mobile: Add "Jump to Plot" link
        is_mobile = st.session_state.get('is_mobile', False)
        if is_mobile:
            st.markdown("📊 [Jump to Plot](#plot-anchor)")

        st.markdown("---")
        st.markdown("### Processing Workflow")

        # **FIX (Issue 6a & 6b)**: Reordered UI sections
        # Render accordion sections in order
        render_processing_range_section(is_expanded=(expanded_section == 'processing_range'))
        render_despike_section(is_expanded=(expanded_section == 'despike'))
        render_baseline_section(is_expanded=(expanded_section == 'baseline'))

        peak_fit_enabled = is_section_enabled('peak_fit', spectrum)
        render_peak_fit_section(
            is_expanded=(expanded_section == 'peak_fit'),
            is_enabled=peak_fit_enabled
        )

        render_export_section(is_expanded=(expanded_section == 'export'))

        st.markdown("---")

        # Reset to Raw button (MOVED below Export per Issue 6a)
        if spectrum is not None:
            if st.button("🔄 Reset to Raw", help="Clear all processing and start over"):
                spectrum.reset_to_raw()
                st.session_state['expanded_section'] = 'processing_range'
                st.success("✅ Reset to raw data")
                st.rerun()

        st.markdown("---")

        # View Options (MOVED below Reset to Raw per Issue 6b)
        render_view_options()
