"""
Unified plot rendering for all processing stages.

This module provides a single Plotly figure that displays multiple
toggleable layers: raw, de-spiked, baseline-corrected, fit results.
"""

import plotly.graph_objects as go
import streamlit as st
from typing import Optional, Dict
from ..models.spectrum import SpectrumFile


def create_empty_figure() -> go.Figure:
    """
    Create an empty placeholder figure.

    Returns
    -------
    go.Figure
        Empty Plotly figure with placeholder text.
    """
    fig = go.Figure()

    fig.add_annotation(
        text="Load a file to view spectrum",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20, color="gray")
    )

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=600,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return fig


def compute_default_visibility(spectrum: SpectrumFile) -> Dict[str, bool]:
    """
    Compute default layer visibility based on processing stage.

    Parameters
    ----------
    spectrum : SpectrumFile
        Spectrum file with processing state.

    Returns
    -------
    dict
        Layer visibility mapping (layer_name -> visible bool).

    Notes
    -----
    Visibility logic (updated):
    - Default on load: Show raw only
    - During preview (preview active): Show both raw + preview layers
    - After despike CONFIRMED: Show despiked only, hide raw
    - After baseline CONFIRMED: Show baseline_corrected only, hide all others
    - After fit CONFIRMED: Show baseline_corrected + fit_total, hide components
    """
    # Get status flags
    despike_done = getattr(spectrum, 'despike_done', False)
    baseline_done = getattr(spectrum, 'baseline_done', False)
    fit_done = getattr(spectrum, 'fit_done', False)

    # Check if previews are active (user is adjusting params)
    import streamlit as st
    despike_preview_active = ('despike_preview' in st.session_state and
                              st.session_state['despike_preview'] is not None)
    baseline_preview_active = ('baseline_preview' in st.session_state and
                               st.session_state['baseline_preview'] is not None)

    visibility = {
        "raw": True,
        "despiked": False,
        "despiked_preview": False,
        "baseline_preview": False,
        "corrected_preview": False,
        "baseline_corrected": False,
        "fit_total": False,
        "components": False
    }

    # Apply visibility rules based on processing stage
    if despike_preview_active:
        # During despike preview: Show raw + despiked preview
        visibility["raw"] = True
        visibility["despiked_preview"] = True
        visibility["despiked"] = False
    elif baseline_preview_active:
        # During baseline preview: Show raw + baseline preview traces
        visibility["raw"] = True
        visibility["baseline_preview"] = True
        visibility["corrected_preview"] = True
        visibility["despiked"] = False
        visibility["baseline_corrected"] = False
    elif fit_done:
        # After fit confirmed: Show corrected + fit only
        visibility["raw"] = False
        visibility["despiked"] = False
        visibility["baseline_corrected"] = True
        visibility["fit_total"] = True
        visibility["components"] = False  # Hidden by default per design.md
    elif baseline_done:
        # After baseline confirmed: Show corrected only
        visibility["raw"] = False
        visibility["despiked"] = False
        visibility["baseline_corrected"] = True
    elif despike_done:
        # After despike confirmed: Show despiked only
        visibility["raw"] = False
        visibility["despiked"] = True

    return visibility


def create_unified_figure(spectrum: SpectrumFile, layer_config: Optional[Dict[str, bool]] = None) -> go.Figure:
    """
    Create unified Plotly figure with multiple toggleable layers.

    Parameters
    ----------
    spectrum : SpectrumFile
        Spectrum file with processing data.
    layer_config : dict, optional
        Layer visibility overrides. If None, uses compute_default_visibility().

    Returns
    -------
    go.Figure
        Plotly figure with all data layers.

    Notes
    -----
    Layer naming convention (from design.md D2):
    - "raw": Raw data (blue, markers)
    - "despiked": De-spiked data (orange, line)
    - "baseline_preview": Preview baseline (red, dash)
    - "corrected_preview": Preview corrected (green, line)
    - "baseline_corrected": Final corrected (purple, line)
    - "fit_total": Fit total curve (black, line)
    - "component_N": Individual fit components (gray, dash)
    """
    if layer_config is None:
        layer_config = compute_default_visibility(spectrum)

    fig = go.Figure()

    # Determine axis labels based on mode
    x_label = "Raman Shift (cm⁻¹)" if spectrum.mode == "Raman" else "Wavelength (nm)"
    y_label = "Intensity (a.u.)"

    # Layer 1: Raw data
    fig.add_trace(go.Scatter(
        x=spectrum.raw_data.X,
        y=spectrum.raw_data.Y,
        mode="markers",
        name="Raw",
        marker=dict(size=3, color="blue"),
        visible=layer_config.get("raw", True)
    ))

    # Layer 2: De-spiked data (if exists)
    despike_applied = spectrum.processing_settings.despike_applied
    if despike_applied:
        fig.add_trace(go.Scatter(
            x=spectrum.processed_data.X,
            y=spectrum.processed_data.Y,
            mode="lines",
            name="De-spiked",
            line=dict(color="orange", width=2),
            visible=layer_config.get("despiked", False)
        ))

    # Layer 2.5: De-spiked preview (if active)
    if 'despike_preview' in st.session_state and st.session_state['despike_preview'] is not None:
        preview_data = st.session_state['despike_preview']
        if 'despiked' in preview_data:
            fig.add_trace(go.Scatter(
                x=preview_data['x'],
                y=preview_data['despiked'],
                mode="lines",
                name="Preview De-spiked",
                line=dict(color="orange", width=2, dash="dash"),
                visible=layer_config.get("despiked_preview", True)
            ))

    # Layer 3: Baseline-corrected data (if exists)
    baseline_applied = spectrum.processing_settings.baseline_applied
    if baseline_applied:
        fig.add_trace(go.Scatter(
            x=spectrum.processed_data.X,
            y=spectrum.processed_data.Y,
            mode="lines",
            name="Baseline-corrected",
            line=dict(color="purple", width=2),
            visible=layer_config.get("baseline_corrected", False)
        ))

    # Layers 4-5: Baseline preview traces (Phase 2.4)
    # These are added dynamically from session state when user adjusts baseline params
    if 'baseline_preview' in st.session_state and st.session_state['baseline_preview'] is not None:
        preview_data = st.session_state['baseline_preview']
        if 'baseline' in preview_data:
            fig.add_trace(go.Scatter(
                x=preview_data['x'],
                y=preview_data['baseline'],
                mode="lines",
                name="Preview Baseline",
                line=dict(color="red", width=2, dash="dash"),
                visible=layer_config.get("baseline_preview", True)
            ))
        if 'corrected' in preview_data:
            fig.add_trace(go.Scatter(
                x=preview_data['x'],
                y=preview_data['corrected'],
                mode="lines",
                name="Preview Corrected",
                line=dict(color="green", width=2),
                opacity=0.6,
                visible=layer_config.get("corrected_preview", True)
            ))

    # Layer 6: Fit total curve (if exists)
    if spectrum.fit_result is not None and spectrum.fit_result.success:
        if hasattr(spectrum.fit_result, 'total_fit_curve') and spectrum.fit_result.total_fit_curve is not None:
            fig.add_trace(go.Scatter(
                x=spectrum.processed_data.X,
                y=spectrum.fit_result.total_fit_curve,
                mode="lines",
                name="Fit Total",
                line=dict(color="black", width=2),
                visible=layer_config.get("fit_total", False)
            ))

    # Layers 7+: Fit components (if exists and show_components enabled)
    if spectrum.fit_result is not None and spectrum.fit_result.success:
        if hasattr(spectrum.fit_result, 'fitted_peaks') and spectrum.fit_result.fitted_peaks:
            if layer_config.get("components", False):
                for i, peak in enumerate(spectrum.fit_result.fitted_peaks):
                    if hasattr(peak, 'component_curve') and peak.component_curve is not None:
                        peak_label = getattr(peak, 'label', f"Peak {i+1}")
                        fig.add_trace(go.Scatter(
                            x=spectrum.processed_data.X,
                            y=peak.component_curve,
                            mode="lines",
                            name=peak_label,
                            line=dict(color="gray", width=1.5, dash="dash"),
                            opacity=0.7,
                            visible=True
                        ))

    # Note: X-range indicators removed - we now crop the data instead of showing indicators

    # Update layout
    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=600,
        hovermode="closest",
        template="plotly_white",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        margin=dict(l=60, r=40, t=40, b=60)
    )

    return fig


def render_unified_plot():
    """
    Render the unified plot in the center panel.

    This function should be called from app.py within the center column.
    """
    spectrum = st.session_state.get("files", {}).get(st.session_state.get("current_file"))

    if spectrum is None:
        # Show empty placeholder
        fig = create_empty_figure()
    else:
        # Get layer visibility from View Options checkboxes (Phase 2.2)
        layer_config = {
            "raw": st.session_state.get("show_raw", True),
            "despiked": st.session_state.get("show_despiked", False),
            "baseline_corrected": st.session_state.get("show_corrected", False),
            "fit_total": st.session_state.get("show_fit", False),
            "components": st.session_state.get("show_components", False)
        }

        fig = create_unified_figure(spectrum, layer_config)

    # Add plot anchor for mobile "Jump to Plot" link
    st.markdown('<div id="plot-anchor"></div>', unsafe_allow_html=True)

    # Render plot
    st.plotly_chart(fig, use_container_width=True, key="unified_plot")
