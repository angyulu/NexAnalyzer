"""Shared Streamlit UI components."""

import streamlit as st
import pandas as pd


def render_peak_results_table(fit_result):
    """Render per-peak fit results as a dataframe (label, center, amplitude, FWHM, shape)."""
    if fit_result is None or not fit_result.success or not fit_result.fitted_peaks:
        return

    rows = []
    for peak in fit_result.fitted_peaks:
        rows.append({
            "Label": peak.label,
            "Center": f"{peak.center:.2f} ± {peak.center_stderr:.2f}",
            "Amplitude": f"{peak.amplitude:.1f} ± {peak.amplitude_stderr:.1f}",
            "FWHM": f"{peak.width_fwhm:.2f} ± {peak.width_stderr:.2f}",
            "Shape": f"{peak.shape:.3f}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)
