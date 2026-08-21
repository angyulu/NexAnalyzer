"""
Static fit figures for export and reports.

Where live_plot.py renders the interactive, session-state-driven multi-layer
plot on the Analysis page, this module builds standalone figures with no
session-state dependencies: the data + fit + components view used for PNG/HTML
export and for the Sample Report's per-point grids.

Rendering these to the page goes through core.viz.render.render_plot().
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
def plot_composite(
    x: np.ndarray,
    y_data: np.ndarray,
    fit_result,  # FitResult object
    mode: str = "Raman",
    title: str = "Peak Fit Results",
    show_components: bool = True,
    show_residuals: bool = True,
) -> go.Figure:
    """
    Create composite plot with data, fit, components, and (optionally) residuals.

    Layout: 3/4 main plot (data + fit + components) + 1/4 residuals subplot,
    or a single full-height main plot when `show_residuals` is False.

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
    show_residuals : bool, default=True
        Whether to include the residuals subplot. False gives a single
        full-height data+fit panel — used where the plot is rendered small
        (e.g. the Sample Report's 3x3 fitted-spectrum grids), where a
        quarter-height residual strip is unreadable anyway.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Interactive Plotly figure with subplots.

    Notes
    -----
    Full implementation will be completed in Phase 5 (T042-T044).
    This is a simplified version for Phase 3 completion.
    """
    # ========== CREATE SUBPLOT LAYOUT ==========
    # Create 2-row, 1-column subplot layout
    # Row 1 (75% height): Main plot with data, fit, and components
    # Row 2 (25% height): Residuals subplot
    # WHY: Residuals subplot helps evaluate fit quality (should be random noise around zero)
    if show_residuals:
        fig = make_subplots(
            rows=2, cols=1,  # 2 rows, 1 column
            row_heights=[0.75, 0.25],  # Row 1 gets 75% of height, Row 2 gets 25%
            vertical_spacing=0.05,  # 5% gap between subplots
            subplot_titles=("Data & Fit", "")  # Titles for each subplot
        )
    else:
        # Single panel: the main plot gets the full figure height
        fig = make_subplots(rows=1, cols=1)

    # ========== DETERMINE AXIS LABEL ==========
    # X-axis label depends on spectroscopy mode
    if mode == "Raman":
        x_label = "Raman Shift (cm⁻¹)"  # Wavenumber shift
    else:  # PL (Photoluminescence)
        x_label = "Wavelength (nm)"  # Emission wavelength

    # ==================== ROW 1: MAIN PLOT - DATA ====================
    # Add baseline-corrected data as scatter plot
    # Color: #1f77b4 (Plotly blue) - standard data color
    # WHY: This is the data that was fitted (after baseline removal)
    fig.add_trace(go.Scatter(
        x=x,  # X values (wavenumber or wavelength)
        y=y_data,  # Processed/baseline-corrected intensity
        mode='markers',  # Show as scatter points (actual data)
        name='Data',  # Legend label
        marker=dict(size=4, color='#1f77b4'),  # Blue dots, slightly larger (4px)
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'  # Custom tooltip
    ), row=1, col=1)  # Add to row 1, column 1 (main plot)

    # ==================== ROW 1: MAIN PLOT - TOTAL FIT ====================
    # Only add fit traces if fit_result exists and fitting succeeded
    if fit_result and fit_result.total_fit_curve is not None:
        # Add total fit curve (sum of all Voigt peak components)
        # Color: #ff7f0e (Plotly orange) - standard fit color
        # WHY: User compares this to data to evaluate R² quality
        fig.add_trace(go.Scatter(
            x=x,  # Same X as data
            y=fit_result.total_fit_curve,  # Sum of all fitted peaks
            mode='lines',  # Connected line (smooth fit)
            name='Total Fit',  # Legend label
            line=dict(width=2, color='#ff7f0e'),  # Orange line, 2-pixel width
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Fit: %{{y:.1f}}<extra></extra>'  # Custom tooltip
        ), row=1, col=1)  # Add to row 1 (main plot)

        # ==================== ROW 1: MAIN PLOT - COMPONENTS ====================
        # Add individual peak components if user enabled "Show Components"
        # Each peak gets its own dashed line trace
        # WHY: User can see contribution of each peak (e.g., D-band vs G-band ratio)
        if show_components and fit_result.fitted_peaks:
            # Loop through each fitted peak
            for i, peak in enumerate(fit_result.fitted_peaks):
                # Only add if component_curve was generated
                if peak.component_curve is not None:
                    # Add individual peak component trace
                    # Dash style: dashed to distinguish from total fit
                    # Opacity: 0.7 (semi-transparent to avoid cluttering)
                    fig.add_trace(go.Scatter(
                        x=x,  # Same X as data and fit
                        y=peak.component_curve,  # Single peak's contribution
                        mode='lines',  # Connected line
                        name=peak.label or f"Peak {i+1}",  # Use peak label or default "Peak 1", "Peak 2", etc.
                        line=dict(width=1.5, dash='dash'),  # Dashed line, thinner than total fit
                        opacity=0.7,  # Semi-transparent
                        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Component: %{{y:.1f}}<extra></extra>'  # Custom tooltip
                    ), row=1, col=1)  # Add to row 1 (main plot)

        # ==================== ROW 2: RESIDUALS SUBPLOT ====================
        # Add residuals (data - fit) to bottom subplot, unless the caller
        # asked for a residual-free single-panel plot
        if show_residuals:
            # -------- RESIDUALS SUBPLOT - DATA POINTS --------
            # Color: #d62728 (Plotly red) - indicates error/residual
            # WHY: Residuals should be random noise around zero if fit is good
            # Patterns in residuals indicate systematic fit errors (e.g., missing peaks)
            fig.add_trace(go.Scatter(
                x=x,  # Same X as data
                y=fit_result.residuals,  # Residuals = data - total_fit (from lmfit)
                mode='markers',  # Show as scatter points (discrete residuals)
                name='Residuals',  # Legend label (but showlegend=False)
                marker=dict(size=3, color='#d62728'),  # Small red dots
                showlegend=False,  # Don't show in legend (avoid clutter)
                hovertemplate=f'{x_label}: %{{x:.2f}}<br>Residual: %{{y:.1f}}<extra></extra>'  # Custom tooltip
            ), row=2, col=1)  # Add to row 2 (residuals subplot)

            # -------- RESIDUALS SUBPLOT - ZERO LINE --------
            # Add horizontal dashed line at Y=0 for reference
            # WHY: Helps visualize whether residuals are centered around zero
            # Good fit: residuals randomly scattered around zero line
            # Bad fit: residuals show systematic trends or offsets
            fig.add_trace(go.Scatter(
                x=[x.min(), x.max()],  # Horizontal line from min X to max X
                y=[0, 0],  # Y=0 (zero line)
                mode='lines',  # Connected line
                line=dict(width=1, color='gray', dash='dash'),  # Thin gray dashed line
                showlegend=False  # Don't show in legend
            ), row=2, col=1)  # Add to row 2 (residuals subplot)

    # ========== CONFIGURE SUBPLOT AXES ==========
    # Update axes labels for each subplot
    # Only bottom subplot (row 2) gets X-axis label (shared X-axis)
    # WHY: Saves vertical space, both subplots use same X-axis
    x_label_row = 2 if show_residuals else 1  # Bottom-most subplot carries the X-axis label
    fig.update_xaxes(title_text=x_label, row=x_label_row, col=1)
    fig.update_yaxes(title_text="Intensity (a.u.)", row=1, col=1)  # Y-axis label for main plot
    if show_residuals:
        fig.update_yaxes(title_text="Residual", row=2, col=1)  # Y-axis label for residuals subplot

    # ========== CONFIGURE OVERALL LAYOUT ==========
    # Set title, interactivity, styling, legend position for entire figure
    fig.update_layout(
        title=title,  # Overall plot title (e.g., "Peak Fit Results")
        hovermode='closest',  # Show hover tooltip for nearest point
        template='plotly_white',  # Clean white background with grid
        height=600,  # Total figure height in pixels (includes both subplots)
        showlegend=True,  # Display legend
        legend=dict(
            x=1.02,  # Position just outside right edge of plot (2% beyond)
            y=1,  # Position at top (100% from bottom)
            bgcolor='rgba(255,255,255,0.8)'  # Semi-transparent white background
        )
    )

    return fig  # Return completed figure (data+fit+components, plus residuals if enabled)
