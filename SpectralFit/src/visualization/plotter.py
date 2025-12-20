"""
Plotly visualization functions for spectroscopy data.

This module provides functions to create:
- Simple preview plots (raw vs processed)
- Composite plots (data + fit + components + residuals)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Optional


def add_x_range_indicators(fig: go.Figure, x_min: float, x_max: float, row: int = 1, col: int = 1):
    """
    Add vertical lines and shading for X-range limiting (v2.1+).

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to modify.
    x_min : float
        Minimum X value for processing range.
    x_max : float
        Maximum X value for processing range.
    row : int, default=1
        Subplot row index (for make_subplots figures).
    col : int, default=1
        Subplot column index (for make_subplots figures).
    """
    # Add vertical lines at boundaries
    fig.add_vline(
        x=x_min,
        line_dash="dash",
        line_color="gray",
        line_width=2,
        annotation_text=f"X min: {x_min:.1f}",
        annotation_position="top",
        row=row, col=col
    )
    fig.add_vline(
        x=x_max,
        line_dash="dash",
        line_color="gray",
        line_width=2,
        annotation_text=f"X max: {x_max:.1f}",
        annotation_position="top",
        row=row, col=col
    )

    # Add shaded region for active range
    fig.add_vrect(
        x0=x_min,
        x1=x_max,
        fillcolor="lightgreen",
        opacity=0.1,
        layer="below",
        line_width=0,
        row=row, col=col
    )


def apply_plot_width(fig: go.Figure, width_preset: str = "Standard"):
    """
    Apply plot width based on preset (v2.1+).

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to modify.
    width_preset : str, default="Standard"
        One of: "Compact" (60%), "Standard" (75%), "Wide" (90%), "Full" (100%).
    """
    width_map = {
        "Compact": 0.6,
        "Standard": 0.75,
        "Wide": 0.9,
        "Full": 1.0
    }
    width_fraction = width_map.get(width_preset, 0.75)

    fig.update_layout(
        width=int(1200 * width_fraction),
        autosize=True
    )


def plot_preview(
    x: np.ndarray,
    y_raw: np.ndarray,
    y_processed: Optional[np.ndarray] = None,
    mode: str = "Raman",
    title: str = "Spectrum Preview",
    width_preset: str = "Standard",
    x_range_enabled: bool = False,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None,
    baseline_preview: Optional[np.ndarray] = None,
    y_corrected_preview: Optional[np.ndarray] = None
) -> go.Figure:
    """
    Create simple preview plot comparing raw and processed spectra.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber (cm⁻¹) or wavelength (nm).
    y_raw : np.ndarray
        Raw intensity.
    y_processed : np.ndarray, optional
        Processed intensity (after despike/baseline). If None, only raw is shown.
    mode : str, default="Raman"
        "Raman" or "PL" (affects axis labels).
    title : str, default="Spectrum Preview"
        Plot title.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Interactive Plotly figure.

    Examples
    --------
    >>> fig = plot_preview(x, y_raw, y_processed, mode="Raman")
    >>> fig.show()  # In Jupyter
    >>> st.plotly_chart(fig, use_container_width=True)  # In Streamlit
    """
    fig = go.Figure()

    # X-axis label
    if mode == "Raman":
        x_label = "Raman Shift (cm⁻¹)"
    else:  # PL
        x_label = "Wavelength (nm)"

    # Add raw data
    fig.add_trace(go.Scatter(
        x=x,
        y=y_raw,
        mode='markers',
        name='Raw Data',
        marker=dict(size=3, color='#1f77b4', opacity=0.6),
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'
    ))

    # Add processed data if provided
    if y_processed is not None:
        fig.add_trace(go.Scatter(
            x=x,
            y=y_processed,
            mode='lines',
            name='Processed',
            line=dict(width=2, color='#ff7f0e'),
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'
        ))

    # Add baseline preview if provided (v2.1+ real-time preview)
    if baseline_preview is not None:
        fig.add_trace(go.Scatter(
            x=x,
            y=baseline_preview,
            mode='lines',
            name='Preview Baseline',
            line=dict(width=2, color='#d62728', dash='dash'),
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Baseline: %{{y:.1f}}<extra></extra>'
        ))

    # Add corrected preview if provided (v2.1+ real-time preview)
    if y_corrected_preview is not None:
        fig.add_trace(go.Scatter(
            x=x,
            y=y_corrected_preview,
            mode='lines',
            name='Preview Corrected',
            line=dict(width=2, color='#2ca02c'),
            opacity=0.6,
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Corrected: %{{y:.1f}}<extra></extra>'
        ))

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="Intensity (a.u.)",
        hovermode='closest',
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)')
    )

    # Apply plot width (v2.1+)
    apply_plot_width(fig, width_preset)

    # Add X-range indicators if enabled (v2.1+)
    if x_range_enabled and x_min is not None and x_max is not None:
        add_x_range_indicators(fig, x_min, x_max)

    return fig


def plot_with_baseline(
    x: np.ndarray,
    y_original: np.ndarray,
    y_corrected: np.ndarray,
    baseline: np.ndarray,
    mode: str = "Raman",
    title: str = "Baseline Correction",
    width_preset: str = "Standard",
    x_range_enabled: bool = False,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None
) -> go.Figure:
    """
    Create plot showing original data, baseline, and corrected data.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber (cm⁻¹) or wavelength (nm).
    y_original : np.ndarray
        Original intensity (before baseline correction).
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve.
    mode : str, default="Raman"
        "Raman" or "PL" (affects axis labels).
    title : str, default="Baseline Correction"
        Plot title.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Interactive Plotly figure.
    """
    fig = go.Figure()

    # X-axis label
    if mode == "Raman":
        x_label = "Raman Shift (cm⁻¹)"
    else:  # PL
        x_label = "Wavelength (nm)"

    # Original data
    fig.add_trace(go.Scatter(
        x=x,
        y=y_original,
        mode='markers',
        name='Original',
        marker=dict(size=3, color='#1f77b4', opacity=0.5),
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'
    ))

    # Baseline
    fig.add_trace(go.Scatter(
        x=x,
        y=baseline,
        mode='lines',
        name='Baseline',
        line=dict(width=2, color='#d62728', dash='dash'),
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Baseline: %{{y:.1f}}<extra></extra>'
    ))

    # Corrected data (offset for clarity)
    offset = baseline.min() - y_corrected.max() - (y_original.max() - y_original.min()) * 0.1
    fig.add_trace(go.Scatter(
        x=x,
        y=y_corrected + offset,
        mode='lines',
        name='Corrected (offset)',
        line=dict(width=2, color='#2ca02c'),
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Corrected: %{{y:.1f}}<extra></extra>'
    ))

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="Intensity (a.u.)",
        hovermode='closest',
        template='plotly_white',
        height=500,
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)')
    )

    # Apply plot width (v2.1+)
    apply_plot_width(fig, width_preset)

    # Add X-range indicators if enabled (v2.1+)
    if x_range_enabled and x_min is not None and x_max is not None:
        add_x_range_indicators(fig, x_min, x_max)

    return fig


def plot_composite(
    x: np.ndarray,
    y_data: np.ndarray,
    fit_result,  # FitResult object
    mode: str = "Raman",
    title: str = "Peak Fit Results",
    show_components: bool = True,
    width_preset: str = "Standard",
    x_range_enabled: bool = False,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None
) -> go.Figure:
    """
    Create composite plot with data, fit, components, and residuals.

    Layout: 3/4 main plot (data + fit + components) + 1/4 residuals subplot.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber (cm⁻¹) or wavelength (nm).
    y_data : np.ndarray
        Processed intensity data.
    fit_result : FitResult
        Fitting results with total_fit_curve, fitted_peaks, residuals.
    mode : str, default="Raman"
        "Raman" or "PL" (affects axis labels).
    title : str, default="Peak Fit Results"
        Plot title.
    show_components : bool, default=True
        Whether to show individual peak components.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Interactive Plotly figure with subplots.

    Notes
    -----
    Full implementation will be completed in Phase 5 (T042-T044).
    This is a simplified version for Phase 3 completion.
    """
    # Create subplots: main plot (75%) + residuals (25%)
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.05,
        subplot_titles=("Data & Fit", "Residuals")
    )

    # X-axis label
    if mode == "Raman":
        x_label = "Raman Shift (cm⁻¹)"
    else:  # PL
        x_label = "Wavelength (nm)"

    # Main plot: Data
    fig.add_trace(go.Scatter(
        x=x,
        y=y_data,
        mode='markers',
        name='Data',
        marker=dict(size=4, color='#1f77b4'),
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'
    ), row=1, col=1)

    # Main plot: Total fit
    if fit_result and fit_result.total_fit_curve is not None:
        fig.add_trace(go.Scatter(
            x=x,
            y=fit_result.total_fit_curve,
            mode='lines',
            name='Total Fit',
            line=dict(width=2, color='#ff7f0e'),
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Fit: %{{y:.1f}}<extra></extra>'
        ), row=1, col=1)

        # Main plot: Components
        if show_components and fit_result.fitted_peaks:
            for i, peak in enumerate(fit_result.fitted_peaks):
                if peak.component_curve is not None:
                    fig.add_trace(go.Scatter(
                        x=x,
                        y=peak.component_curve,
                        mode='lines',
                        name=peak.label or f"Peak {i+1}",
                        line=dict(width=1.5, dash='dash'),
                        opacity=0.7,
                        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Component: %{{y:.1f}}<extra></extra>'
                    ), row=1, col=1)

        # Residuals subplot
        fig.add_trace(go.Scatter(
            x=x,
            y=fit_result.residuals,
            mode='markers',
            name='Residuals',
            marker=dict(size=3, color='#d62728'),
            showlegend=False,
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Residual: %{{y:.1f}}<extra></extra>'
        ), row=2, col=1)

        # Zero line in residuals
        fig.add_trace(go.Scatter(
            x=[x.min(), x.max()],
            y=[0, 0],
            mode='lines',
            line=dict(width=1, color='gray', dash='dash'),
            showlegend=False
        ), row=2, col=1)

    # Update axes
    fig.update_xaxes(title_text=x_label, row=2, col=1)
    fig.update_yaxes(title_text="Intensity (a.u.)", row=1, col=1)
    fig.update_yaxes(title_text="Residual", row=2, col=1)

    # Layout
    fig.update_layout(
        title=title,
        hovermode='closest',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(x=1.02, y=1, bgcolor='rgba(255,255,255,0.8)')
    )

    # Apply plot width (v2.1+)
    apply_plot_width(fig, width_preset)

    # Add X-range indicators if enabled (v2.1+)
    if x_range_enabled and x_min is not None and x_max is not None:
        add_x_range_indicators(fig, x_min, x_max, row=1, col=1)

    return fig
