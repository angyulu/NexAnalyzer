"""
Pre-processing tab UI component.

This tab provides:
- De-spiking controls (modified Z-score)
- Baseline correction controls (polynomial / ALS)
- Preview plots
- Reset to Raw button
"""

import streamlit as st
import numpy as np
from .session_state import get_current_spectrum
from ..processing.despiking import remove_spikes, count_spikes
from ..processing.baseline import (
    baseline_polynomial_with_autoshift,
    baseline_als_with_autoshift
)
from ..models.spectrum import SpectrumData


def render_preprocess_tab():
    """
    Render pre-processing tab (de-spike and baseline correction).

    This function should be called from app.py within a tab context.
    """
    spectrum = get_current_spectrum()

    if spectrum is None:
        st.info("📁 Upload a spectrum file to begin pre-processing")
        return

    st.header(f"Pre-process: {spectrum.filename}")

    # Processing Range section (v2.1+)
    st.subheader("Processing Range")

    # Get data range
    X = spectrum.processed_data.X
    x_min_data, x_max_data = X.min(), X.max()

    # Checkbox to enable X-range limiting
    x_range_enabled = st.checkbox(
        "Limit to X range",
        value=spectrum.x_range_enabled,
        help="Process only a specific region of the spectrum"
    )

    # Numeric inputs for X min/max
    col1, col2 = st.columns(2)

    with col1:
        x_min = st.number_input(
            f"X min ({spectrum.mode} units)",
            value=spectrum.x_min if spectrum.x_min is not None else x_min_data,
            min_value=float(x_min_data),
            max_value=float(x_max_data),
            disabled=not x_range_enabled,
            help="Minimum X value for processing"
        )

    with col2:
        x_max = st.number_input(
            f"X max ({spectrum.mode} units)",
            value=spectrum.x_max if spectrum.x_max is not None else x_max_data,
            min_value=float(x_min_data),
            max_value=float(x_max_data),
            disabled=not x_range_enabled,
            help="Maximum X value for processing"
        )

    # Validate and save
    if x_range_enabled and x_min >= x_max:
        st.error("X min must be less than X max")
    else:
        spectrum.x_range_enabled = x_range_enabled
        spectrum.x_min = x_min if x_range_enabled else None
        spectrum.x_max = x_max if x_range_enabled else None

    st.markdown("---")

    # De-spiking section
    st.subheader("1. Remove Cosmic-Ray Spikes")
    st.caption("Modified Z-score algorithm (MAD-based)")

    threshold = st.slider(
        "Sensitivity Threshold",
        min_value=3.0,
        max_value=15.0,
        value=spectrum.processing_settings.despike_threshold,
        step=0.5,
        help="Higher = less sensitive (fewer spikes detected)\nDefault: 6.0"
    )

    if st.button("Run Spike Removal"):
        try:
            # Update threshold in settings
            spectrum.processing_settings.despike_threshold = threshold

            # Run de-spiking on current processed data
            y_clean, spike_mask = remove_spikes(
                spectrum.processed_data.Y,
                threshold=threshold
            )

            # Update processed data (keep X unchanged)
            spectrum.processed_data = SpectrumData(
                X=spectrum.processed_data.X,
                Y=y_clean
            )

            # Mark as applied
            spectrum.processing_settings.despike_applied = True

            # Report results
            n_spikes = count_spikes(spike_mask)
            frac = n_spikes / len(spike_mask) * 100
            st.success(f"✅ Removed {n_spikes} spikes ({frac:.2f}% of points)")

        except Exception as e:
            st.error(f"❌ Spike removal failed: {e}")

    if spectrum.processing_settings.despike_applied:
        st.caption("✓ Spike removal has been applied")

    st.markdown("---")

    # Baseline correction section
    st.subheader("2. Correct Baseline")

    baseline_alg = st.radio(
        "Algorithm",
        ["Polynomial", "ALS"],
        index=0 if spectrum.processing_settings.baseline_algorithm == "Polynomial" else 1,
        help="Polynomial: Simple fitting\nALS: Asymmetric Least Squares (better for fluorescence)\n\nNegative Y values are automatically handled via internal shifting"
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
            min_value=1000.0,
            max_value=1000000.0,
            value=spectrum.processing_settings.baseline_lambda,
            step=1000.0,
            format="%.0f",
            help="Higher = smoother baseline"
        )
        p_val = st.slider(
            "Asymmetry (p)",
            min_value=0.001,
            max_value=0.1,
            value=spectrum.processing_settings.baseline_p,
            step=0.001,
            format="%.3f",
            help="Lower = more asymmetric (weights below baseline)"
        )

    # Real-time preview computation (v2.1+)
    # Compute baseline preview on every parameter change for instant visual feedback
    if baseline_alg == "Polynomial":
        cache_key = f"{spectrum.filename}_Polynomial_{degree}"
        params = {'degree': degree}
    else:
        cache_key = f"{spectrum.filename}_ALS_{lambda_val}_{p_val}"
        params = {'lambda': lambda_val, 'p': p_val}

    # Check if preview needs recomputation
    current_preview = st.session_state.get('baseline_preview')
    needs_recompute = (
        current_preview is None or
        current_preview.get('cache_key') != cache_key
    )

    if needs_recompute:
        with st.spinner("Computing baseline preview..."):
            # Get input data (current processed state, respects prior despike)
            x = spectrum.processed_data.X
            y = spectrum.processed_data.Y

            # Compute baseline using current parameters
            if baseline_alg == "Polynomial":
                y_corrected, baseline_curve, shift = baseline_polynomial_with_autoshift(
                    x, y, degree=degree
                )
            else:  # ALS
                y_corrected, baseline_curve, shift = baseline_als_with_autoshift(
                    x, y, lambda_=lambda_val, p=p_val
                )

            # Cache result in session state
            st.session_state['baseline_preview'] = {
                'cache_key': cache_key,
                'baseline_curve': baseline_curve,
                'y_corrected': y_corrected,
                'shift': shift,
                'algorithm': baseline_alg,
                'params': params
            }

    if st.button("Run Baseline Correction"):
        try:
            # Check if preview exists with matching cache key (v2.1+ optimization)
            preview = st.session_state.get('baseline_preview')

            if preview and preview.get('cache_key') == cache_key:
                # Use cached preview result (instant apply, no recomputation)
                y_corrected = preview['y_corrected']
                baseline_curve = preview['baseline_curve']
                shift = preview['shift']
            else:
                # Fallback: Recompute if preview missing (shouldn't happen in normal flow)
                st.warning("⚠️ Preview cache miss, recomputing...")
                x = spectrum.processed_data.X
                y = spectrum.processed_data.Y

                if baseline_alg == "Polynomial":
                    y_corrected, baseline_curve, shift = baseline_polynomial_with_autoshift(
                        x, y, degree=degree
                    )
                else:  # ALS
                    y_corrected, baseline_curve, shift = baseline_als_with_autoshift(
                        x, y, lambda_=lambda_val, p=p_val
                    )

            # Update settings
            spectrum.processing_settings.baseline_algorithm = baseline_alg
            if baseline_alg == "Polynomial":
                spectrum.processing_settings.baseline_degree = degree
            else:
                spectrum.processing_settings.baseline_lambda = lambda_val
                spectrum.processing_settings.baseline_p = p_val

            # Save shift amount
            spectrum.processing_settings.y_shift = shift

            # Apply baseline correction to processed data
            spectrum.processed_data = SpectrumData(
                X=spectrum.processed_data.X,
                Y=y_corrected
            )

            # Mark as applied
            spectrum.processing_settings.baseline_applied = True

            # Clear preview from session state after applying
            st.session_state['baseline_preview'] = None

            st.success(f"✅ Baseline corrected using {baseline_alg}")

            # Display status if shift was applied
            if shift > 0:
                st.info(f"📊 Applied automatic Y-shift: {shift:.2f} for baseline stability", icon="📊")

        except Exception as e:
            st.error(f"❌ Baseline correction failed: {e}")

    if spectrum.processing_settings.baseline_applied:
        st.caption(f"✓ Baseline correction applied ({spectrum.processing_settings.baseline_algorithm})")

    st.markdown("---")

    # Reset button
    if st.button("Reset to Raw"):
        spectrum.reset_to_raw()
        # Clear preview cache to avoid showing stale preview (v2.1+)
        st.session_state['baseline_preview'] = None
        st.success("✅ Reset to raw data")
        st.rerun()

    # Preview plot
    st.subheader("Preview")

    # Get preview data if available (v2.1+ real-time preview)
    preview = st.session_state.get('baseline_preview')
    baseline_curve_preview = preview['baseline_curve'] if preview else None
    y_corrected_preview = preview['y_corrected'] if preview else None

    # Update caption based on preview state
    if preview:
        st.caption("Plot shows: Raw (blue) vs Processed (orange) vs Preview Baseline (red dashed) & Corrected (green)")
    else:
        st.caption("Plot shows: Raw data (blue markers) vs Processed data (orange line)")

    try:
        from ..visualization.plotter import plot_preview

        # Get plot width from session state (v2.1+)
        width_preset = st.session_state.get("plot_width_preset", "Full")

        fig = plot_preview(
            x=spectrum.raw_data.X,
            y_raw=spectrum.raw_data.Y,
            y_processed=spectrum.processed_data.Y,
            mode=spectrum.mode,
            title=f"Preview: {spectrum.filename}",
            width_preset=width_preset,
            x_range_enabled=spectrum.x_range_enabled,
            x_min=spectrum.x_min,
            x_max=spectrum.x_max,
            # Pass preview data (v2.1+ real-time preview)
            baseline_preview=baseline_curve_preview,
            y_corrected_preview=y_corrected_preview
        )

        from ..visualization.plotter import render_plot
        render_plot(fig)

        # Add helpful caption if no preview yet
        if preview is None:
            st.caption("💡 Adjust baseline parameters above to see live preview")

    except Exception as e:
        st.error(f"❌ Preview plot failed: {e}")
