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

        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Show Raw", value=True, key="show_raw")
            st.checkbox("Show De-spiked", value=False, key="show_despiked")
            st.checkbox("Show Baseline-corrected", value=False, key="show_corrected")
        with col2:
            st.checkbox("Show Fit", value=False, key="show_fit")
            st.checkbox("Show Components", value=False, key="show_components")

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

        threshold = st.slider(
            "Sensitivity Threshold",
            min_value=3.0,
            max_value=15.0,
            value=spectrum.processing_settings.despike_threshold,
            step=0.5,
            help="Higher = less sensitive (fewer spikes detected)\nDefault: 6.0"
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
            ["Polynomial", "ALS"],
            index=0 if spectrum.processing_settings.baseline_algorithm == "Polynomial" else 1,
            help="Polynomial: Simple fitting\nALS: Asymmetric Least Squares (better for fluorescence)"
        )

        # Enable real-time preview toggle
        show_preview = st.checkbox(
            "Show Real-Time Preview",
            value=True,
            help="Update plot preview as you adjust parameters"
        )

        if baseline_alg == "Polynomial":
            degree = st.slider(
                "Polynomial Degree",
                min_value=1,
                max_value=10,
                value=spectrum.processing_settings.baseline_degree,
                help="Higher = more flexible (may overfit)"
            )
            lambda_val = None
            p_val = None
        else:  # ALS
            degree = None
            lambda_val = st.slider(
                "Smoothness (λ)",
                min_value=10000.0,
                max_value=10000000.0,
                value=max(spectrum.processing_settings.baseline_lambda, 100000.0),
                step=10000.0,
                format="%.0f",
                help="Higher = smoother baseline (typical: 100k-1M for fluorescence)"
            )
            p_val = st.slider(
                "Asymmetry (p)",
                min_value=0.0001,
                max_value=0.01,
                value=min(spectrum.processing_settings.baseline_p, 0.001),
                step=0.0001,
                format="%.4f",
                help="Lower = more asymmetric (weights below baseline more)"
            )

        # Real-time preview computation
        if show_preview:
            try:
                X = spectrum.processed_data.X
                Y = spectrum.processed_data.Y

                if baseline_alg == "Polynomial":
                    y_corrected_preview, baseline_preview, y_shift = baseline_polynomial_with_autoshift(
                        X, Y, degree=degree
                    )
                else:
                    y_corrected_preview, baseline_preview, y_shift = baseline_als_with_autoshift(
                        X, Y, lambda_=lambda_val, p=p_val
                    )

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
                # Update settings
                spectrum.processing_settings.baseline_algorithm = baseline_alg
                if baseline_alg == "Polynomial":
                    spectrum.processing_settings.baseline_degree = degree
                else:
                    spectrum.processing_settings.baseline_lambda = lambda_val
                    spectrum.processing_settings.baseline_p = p_val

                # Run baseline correction
                X = spectrum.processed_data.X
                Y = spectrum.processed_data.Y

                if baseline_alg == "Polynomial":
                    y_corrected, baseline, y_shift = baseline_polynomial_with_autoshift(
                        X, Y, degree=degree
                    )
                else:
                    y_corrected, baseline, y_shift = baseline_als_with_autoshift(
                        X, Y, lambda_=lambda_val, p=p_val
                    )

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

                st.success(f"✅ Baseline corrected (Y-shift: {y_shift:.1f})")

                # Auto-expand next section
                st.session_state['expanded_section'] = 'peak_fit'
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
            st.info("No peaks defined. Click 'Auto-Find' or 'Add Peak'")
        else:
            import pandas as pd
            import numpy as np

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
                num_rows="fixed",  # Don't allow add/delete via table (use buttons instead)
                key="peak_table_editor"
            )

            # Sync edits back to spectrum.peak_table
            validation_errors = []

            # Update existing peaks in-place
            for i, row in edited_df.iterrows():
                # Validate row
                errors = validate_peak_row(row, x_range, spectral_resolution)
                if errors:
                    validation_errors.extend(errors)
                    continue

                peak = spectrum.peak_table[i]
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

    # Mobile: Add "Jump to Plot" link
    is_mobile = st.session_state.get('is_mobile', False)
    if is_mobile:
        st.markdown("📊 [Jump to Plot](#plot-anchor)")

    # View Options (always at top)
    render_view_options()

    st.markdown("---")
    st.markdown("### Processing Workflow")

    # Reset to Raw button (global)
    if spectrum is not None:
        if st.button("🔄 Reset to Raw", help="Clear all processing and start over"):
            spectrum.reset_to_raw()
            st.session_state['expanded_section'] = 'processing_range'
            st.success("✅ Reset to raw data")
            st.rerun()

    st.markdown("---")

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
