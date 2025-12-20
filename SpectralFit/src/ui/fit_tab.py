"""
Peak fitting tab UI component.

This tab provides:
- Peak table editor (add/remove peaks, manual guesses)
- Auto-find peaks button
- Run Voigt fitting button
- Fit results display
"""

import streamlit as st
import pandas as pd
from .session_state import get_current_spectrum
from ..models.peak import PeakDefinition
from ..processing.fitting import fit_voigt_peaks, auto_find_peaks


def render_fit_tab():
    """
    Render peak fitting tab (peak table and Voigt fitting).

    This function should be called from app.py within a tab context.
    """
    spectrum = get_current_spectrum()

    if spectrum is None:
        st.info("📁 Upload a spectrum file to begin fitting")
        return

    st.header(f"Fit Peaks: {spectrum.filename}")

    # Check if pre-processing is recommended
    if not spectrum.processing_settings.baseline_applied:
        st.warning("⚠️ Recommended: Apply baseline correction before fitting (Pre-process tab)")

    # Peak table section
    st.subheader("Peak Definitions")
    st.caption("Define initial guesses for peak centers, amplitudes, and widths")

    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("Auto-Find Peaks"):
            try:
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

        if st.button("Add Peak"):
            # Add a new peak at center of X range
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

        if len(spectrum.peak_table) > 0 and st.button("Clear All"):
            spectrum.peak_table = []
            st.rerun()

    with col1:
        if len(spectrum.peak_table) == 0:
            st.info("No peaks defined. Click 'Auto-Find Peaks' or 'Add Peak' to begin.")
        else:
            # Display peak table as editable dataframe
            peak_data = []
            for i, peak in enumerate(spectrum.peak_table):
                peak_data.append({
                    "ID": i,
                    "Label": peak.label,
                    "Center": f"{peak.center:.2f}",
                    "Amplitude": f"{peak.amplitude:.1f}",
                    "FWHM": f"{peak.width_fwhm:.2f}",
                    "Shape": f"{peak.shape:.2f}"
                })

            df = pd.DataFrame(peak_data)
            st.dataframe(df, hide_index=True, use_container_width=True)

            # Remove peak selector
            if len(spectrum.peak_table) > 0:
                remove_id = st.selectbox(
                    "Remove peak:",
                    options=list(range(len(spectrum.peak_table))),
                    format_func=lambda i: f"{spectrum.peak_table[i].label} @ {spectrum.peak_table[i].center:.2f}"
                )
                if st.button("Remove Selected"):
                    del spectrum.peak_table[remove_id]
                    st.rerun()

    st.markdown("---")

    # Fitting controls
    st.subheader("Run Fitting")

    if len(spectrum.peak_table) == 0:
        st.warning("Define at least 1 peak before fitting")
    else:
        # X-range checkbox (v2.1+)
        fit_in_range = False
        if spectrum.x_range_enabled:
            fit_in_range = st.checkbox(
                "Fit only within X range",
                value=True,  # Default ON
                help=f"Fit peaks only in [{spectrum.x_min:.1f}, {spectrum.x_max:.1f}]"
            )

        with st.expander("Advanced Options", expanded=False):
            st.caption(
                f"Auto-bounds: Center ±{'5 cm⁻¹' if spectrum.mode == 'Raman' else '30 nm'}, "
                f"Width 2.5×resolution to 50% of range, Amplitude 0 to 2×max"
            )
            st.caption("Manual bounds override will be implemented in future update")

        if st.button("Run Voigt Fit"):
            if len(spectrum.peak_table) > 10:
                st.error("❌ Maximum 10 peaks allowed")
            else:
                try:
                    # Filter data by X-range if enabled (v2.1+)
                    X_full = spectrum.processed_data.X
                    Y_full = spectrum.processed_data.Y

                    if fit_in_range and spectrum.x_range_enabled:
                        import numpy as np
                        mask = (X_full >= spectrum.x_min) & (X_full <= spectrum.x_max)
                        X_fit = X_full[mask]
                        Y_fit = Y_full[mask]

                        if len(X_fit) < 10:
                            st.error("❌ Not enough data points in X range (need at least 10)")
                            st.stop()
                    else:
                        X_fit = X_full
                        Y_fit = Y_full

                    with st.spinner("Fitting in progress..."):
                        fit_result = fit_voigt_peaks(
                            X_fit,
                            Y_fit,
                            spectrum.peak_table,
                            mode=spectrum.mode
                        )

                        spectrum.fit_result = fit_result

                        if fit_result.success:
                            st.success(
                                f"✅ Fit converged in {fit_result.convergence_time:.2f}s | "
                                f"R² = {fit_result.r_squared:.4f} | "
                                f"χ² = {fit_result.chi_squared:.2e}"
                            )
                            st.rerun()
                        else:
                            st.error(f"❌ {fit_result.error_message}")

                except Exception as e:
                    st.error(f"❌ Fitting failed: {e}")

    st.markdown("---")

    # Results display
    st.subheader("Fit Results")

    if spectrum.fit_result is None:
        st.caption("No fit results yet. Define peaks and run fitting.")
    else:
        if spectrum.fit_result.success:
            st.success(
                f"✓ Fit successful | R² = {spectrum.fit_result.r_squared:.4f} | "
                f"χ² = {spectrum.fit_result.chi_squared:.2e} | "
                f"Time: {spectrum.fit_result.convergence_time:.2f}s"
            )

            # Results table
            results_data = []
            for peak in spectrum.fit_result.fitted_peaks:
                results_data.append({
                    "Label": peak.label,
                    "Center": f"{peak.center:.2f} ± {peak.center_stderr:.2f}",
                    "Amplitude": f"{peak.amplitude:.1f} ± {peak.amplitude_stderr:.1f}",
                    "FWHM": f"{peak.width_fwhm:.2f} ± {peak.width_stderr:.2f}",
                    "Shape": f"{peak.shape:.3f}",
                })

            df_results = pd.DataFrame(results_data)
            st.dataframe(df_results, hide_index=True, use_container_width=True)

            # Plot preview
            st.caption("Full visualization available in Export tab")

            try:
                from ..visualization.plotter import plot_composite

                # Get plot width from session state (v2.1+)
                width_preset = st.session_state.get("plot_width_preset", "Standard")

                fig = plot_composite(
                    spectrum.processed_data.X,
                    spectrum.processed_data.Y,
                    spectrum.fit_result,
                    mode=spectrum.mode,
                    title=f"Fit Results: {spectrum.filename}",
                    show_components=True,
                    width_preset=width_preset,
                    x_range_enabled=spectrum.x_range_enabled,
                    x_min=spectrum.x_min,
                    x_max=spectrum.x_max
                )

                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Plot failed: {e}")

        else:
            st.error(f"❌ Fit failed: {spectrum.fit_result.error_message}")
