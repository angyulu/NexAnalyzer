"""
Plotly visualization functions for spectroscopy data.

This module provides helper functions to create various plot types for
spectroscopy analysis. These functions are used by the main application
for creating standalone plots and exports.

Key Functions:
--------------
- add_x_range_indicators(): Adds visual markers for X-range cropping (DEPRECATED in v2.2)
- apply_plot_width(): Applies width presets (Compact/Standard/Wide/Full)
- plot_preview(): Creates simple 2-trace comparison plot (raw vs processed)
- plot_with_baseline(): Creates 3-trace plot (original + baseline + corrected)
- plot_composite(): Creates multi-panel plot (data + fit + components + residuals)

Note:
-----
In v2.2+, the main plotting is handled by unified_plot.py which uses Plotly
directly without these helper functions. This module is maintained for:
- Backward compatibility with v2.0/v2.1 projects
- Export functionality (saving standalone plots to PNG/HTML)
- Testing and development utilities

Differences from unified_plot.py:
---------------------------------
- unified_plot.py: Multi-layer interactive plot with session state integration
- plotter.py: Standalone plot generation without session state dependencies
"""

# ==================== IMPORTS ====================
import plotly.graph_objects as go  # Plotly graphing library for interactive plots
from plotly.subplots import make_subplots  # Function to create subplot layouts (multi-panel plots)
import numpy as np  # NumPy for array operations
from typing import Optional  # Type hints for optional parameters


def add_x_range_indicators(fig: go.Figure, x_min: float, x_max: float, row: int = 1, col: int = 1):
    """
    Add vertical lines and shading for X-range limiting (v2.1+).

    DEPRECATED in v2.2: No longer used. In v2.2+, we crop data arrays directly
    instead of showing indicators on full-range plots.

    This function adds visual markers to indicate which portion of the spectrum
    will be used for processing (de-spiking, baseline, fitting).

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to modify (will add shapes and annotations).
    x_min : float
        Minimum X value for processing range (left boundary).
    x_max : float
        Maximum X value for processing range (right boundary).
    row : int, default=1
        Subplot row index (for make_subplots figures, 1-indexed).
    col : int, default=1
        Subplot column index (for make_subplots figures, 1-indexed).

    Notes
    -----
    Visual elements added:
    1. Two vertical dashed gray lines at x_min and x_max
    2. Text annotations showing exact boundary values
    3. Light green shaded rectangle between boundaries (10% opacity)
    """
    # ========== LEFT BOUNDARY LINE ==========
    # Add vertical dashed line at minimum X value
    fig.add_vline(
        x=x_min,  # X coordinate for vertical line
        line_dash="dash",  # Dashed line style (not solid)
        line_color="gray",  # Gray color (neutral, not distracting)
        line_width=2,  # 2-pixel width for visibility
        annotation_text=f"X min: {x_min:.1f}",  # Label showing exact value (1 decimal)
        annotation_position="top",  # Place label at top of plot
        row=row, col=col  # Subplot position (for multi-panel plots)
    )

    # ========== RIGHT BOUNDARY LINE ==========
    # Add vertical dashed line at maximum X value
    fig.add_vline(
        x=x_max,  # X coordinate for vertical line
        line_dash="dash",  # Dashed line style
        line_color="gray",  # Gray color
        line_width=2,  # 2-pixel width
        annotation_text=f"X max: {x_max:.1f}",  # Label showing exact value
        annotation_position="top",  # Place label at top
        row=row, col=col  # Subplot position
    )

    # ========== SHADED ACTIVE RANGE ==========
    # Add semi-transparent rectangle to highlight active X-range
    # WHY: Provides visual feedback of which data region will be processed
    fig.add_vrect(
        x0=x_min,  # Left edge of rectangle (minimum X)
        x1=x_max,  # Right edge of rectangle (maximum X)
        fillcolor="lightgreen",  # Light green fill (indicates "active" region)
        opacity=0.1,  # 10% opacity (very subtle, doesn't obscure data)
        layer="below",  # Draw behind data traces (not on top)
        line_width=0,  # No border outline (just filled rectangle)
        row=row, col=col  # Subplot position
    )


def apply_plot_width(fig: go.Figure, width_preset: str = "Standard"):
    """
    Apply plot width based on preset (v2.1+).

    This function sets the plot width using predefined size presets.
    Useful for export functionality where fixed widths are needed.

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to modify (changes layout.width).
    width_preset : str, default="Standard"
        One of: "Compact" (60%), "Standard" (75%), "Wide" (90%), "Full" (100%).
        If invalid preset provided, defaults to "Standard" (75%).

    Notes
    -----
    Base width is 1200 pixels:
    - Compact: 1200 × 0.6 = 720 pixels
    - Standard: 1200 × 0.75 = 900 pixels
    - Wide: 1200 × 0.9 = 1080 pixels
    - Full: 1200 × 1.0 = 1200 pixels

    The autosize=True setting allows Plotly to adjust height proportionally.
    """
    # Map preset names to width fractions (percentage of base width)
    width_map = {
        "Compact": 0.6,   # 60% of base width (720px) - small plots for reports
        "Standard": 0.75,  # 75% of base width (900px) - default balanced size
        "Wide": 0.9,       # 90% of base width (1080px) - wide plots for presentations
        "Full": 1.0        # 100% of base width (1200px) - maximum width
    }

    # Get fraction for requested preset (default to 0.75 if invalid preset)
    width_fraction = width_map.get(width_preset, 0.75)

    # Apply width to figure layout
    # Base width: 1200 pixels (chosen to work well on most screens)
    # autosize=True allows Plotly to adjust other dimensions proportionally
    fig.update_layout(
        width=int(1200 * width_fraction),  # Convert to integer pixels
        autosize=True  # Enable automatic sizing for responsive behavior
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
    # Create empty Plotly Figure object - we'll add traces below
    fig = go.Figure()

    # ========== DETERMINE AXIS LABEL ==========
    # X-axis label depends on spectroscopy mode
    if mode == "Raman":
        x_label = "Raman Shift (cm⁻¹)"  # Wavenumber shift from laser line
    else:  # PL (Photoluminescence)
        x_label = "Wavelength (nm)"  # Emission wavelength

    # ========== TRACE 1: RAW DATA ==========
    # Add raw data as scatter plot (markers, not connected line)
    # Color: #1f77b4 (standard Plotly blue)
    # WHY: Markers show discrete measurement points, useful for seeing data density
    fig.add_trace(go.Scatter(
        x=x,  # X values (wavenumber or wavelength)
        y=y_raw,  # Raw intensity values
        mode='markers',  # Show as scatter points, not line
        name='Raw Data',  # Legend label
        marker=dict(size=3, color='#1f77b4', opacity=0.6),  # Small blue semi-transparent dots
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'  # Custom tooltip
    ))

    # ========== TRACE 2: PROCESSED DATA (OPTIONAL) ==========
    # Add processed data if provided (e.g., after de-spiking or baseline correction)
    # Color: #ff7f0e (standard Plotly orange)
    # WHY: Line mode shows smooth processed result for comparison with raw data
    if y_processed is not None:
        fig.add_trace(go.Scatter(
            x=x,  # Same X values as raw
            y=y_processed,  # Processed intensity values
            mode='lines',  # Show as connected line (smooth curve)
            name='Processed',  # Legend label
            line=dict(width=2, color='#ff7f0e'),  # Orange line, 2-pixel width
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'  # Custom tooltip
        ))

    # ========== TRACE 3: BASELINE PREVIEW (OPTIONAL) ==========
    # Add baseline preview if provided (v2.1+ real-time preview feature)
    # Color: #d62728 (Plotly red) - indicates warning/preview state
    # Dash style: dashed to indicate temporary/preview state
    # WHY: User sees baseline curve shape before clicking "Apply"
    if baseline_preview is not None:
        fig.add_trace(go.Scatter(
            x=x,  # Same X values
            y=baseline_preview,  # Baseline curve Y values (to be subtracted)
            mode='lines',  # Connected line
            name='Preview Baseline',  # Legend label shows this is preview
            line=dict(width=2, color='#d62728', dash='dash'),  # Red dashed line
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Baseline: %{{y:.1f}}<extra></extra>'  # Custom tooltip
        ))

    # ========== TRACE 4: CORRECTED PREVIEW (OPTIONAL) ==========
    # Add corrected preview if provided (v2.1+ real-time preview)
    # Color: #2ca02c (Plotly green) - indicates corrected/processed state
    # Opacity: 0.6 (semi-transparent to avoid cluttering plot)
    # NOTE: This trace was REMOVED in v2.2 per user request, but code kept for backward compatibility
    if y_corrected_preview is not None:
        fig.add_trace(go.Scatter(
            x=x,  # Same X values
            y=y_corrected_preview,  # Baseline-corrected intensity values (preview)
            mode='lines',  # Connected line
            name='Preview Corrected',  # Legend label
            line=dict(width=2, color='#2ca02c'),  # Green line
            opacity=0.6,  # Semi-transparent (60% opacity)
            hovertemplate=f'{x_label}: %{{x:.2f}}<br>Corrected: %{{y:.1f}}<extra></extra>'  # Custom tooltip
        ))

    # ========== CONFIGURE PLOT LAYOUT ==========
    # Set title, axis labels, interactivity, styling, legend position
    fig.update_layout(
        title=title,  # Plot title (e.g., "Spectrum Preview")
        xaxis_title=x_label,  # X-axis label (Raman Shift or Wavelength)
        yaxis_title="Intensity (a.u.)",  # Y-axis label (arbitrary units)
        hovermode='closest',  # Show hover tooltip for nearest data point
        template='plotly_white',  # Clean white background with light grid
        height=400,  # Fixed height in pixels (smaller than main unified plot)
        showlegend=True,  # Display legend
        legend=dict(
            x=0.02,  # Position 2% from left edge (top-left corner)
            y=0.98,  # Position 98% from bottom (near top)
            bgcolor='rgba(255,255,255,0.8)'  # Semi-transparent white background
        )
    )

    # ========== APPLY WIDTH PRESET ==========
    # Apply user-selected width preset (Compact/Standard/Wide/Full)
    apply_plot_width(fig, width_preset)

    # ========== ADD X-RANGE INDICATORS (OPTIONAL) ==========
    # Add visual markers for X-range cropping if enabled
    # NOTE: This feature is DEPRECATED in v2.2 (data arrays are cropped directly now)
    if x_range_enabled and x_min is not None and x_max is not None:
        add_x_range_indicators(fig, x_min, x_max)

    return fig  # Return completed Plotly Figure object


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
    # Create empty Plotly Figure object
    fig = go.Figure()

    # ========== DETERMINE AXIS LABEL ==========
    # X-axis label depends on spectroscopy mode
    if mode == "Raman":
        x_label = "Raman Shift (cm⁻¹)"  # Wavenumber shift
    else:  # PL (Photoluminescence)
        x_label = "Wavelength (nm)"  # Emission wavelength

    # ========== TRACE 1: ORIGINAL DATA ==========
    # Add original data (before baseline correction)
    # Color: #1f77b4 (Plotly blue)
    # Opacity: 0.5 (semi-transparent to show baseline underneath)
    # WHY: User can see original data with background fluorescence
    fig.add_trace(go.Scatter(
        x=x,  # X values (wavenumber or wavelength)
        y=y_original,  # Original intensity (with baseline/background)
        mode='markers',  # Show as scatter points
        name='Original',  # Legend label
        marker=dict(size=3, color='#1f77b4', opacity=0.5),  # Small blue semi-transparent dots
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Intensity: %{{y:.1f}}<extra></extra>'  # Custom tooltip
    ))

    # ========== TRACE 2: BASELINE CURVE ==========
    # Add fitted baseline curve (to be subtracted from original)
    # Color: #d62728 (Plotly red) - warning/preview color
    # Dash style: dashed to indicate this is not actual data
    # WHY: Shows the background curve that will be removed
    fig.add_trace(go.Scatter(
        x=x,  # Same X values
        y=baseline,  # Baseline curve Y values (fitted by algorithm)
        mode='lines',  # Connected line
        name='Baseline',  # Legend label
        line=dict(width=2, color='#d62728', dash='dash'),  # Red dashed line
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Baseline: %{{y:.1f}}<extra></extra>'  # Custom tooltip
    ))

    # ========== TRACE 3: CORRECTED DATA (OFFSET) ==========
    # Add baseline-corrected data (original - baseline)
    # IMPORTANT: Offset vertically downward for visual clarity (avoid overlap with original)
    # Offset calculation: Place corrected data below baseline with 10% gap
    # Color: #2ca02c (Plotly green) - indicates corrected/processed state
    # WHY: User can see result of baseline subtraction without overlap
    offset = baseline.min() - y_corrected.max() - (y_original.max() - y_original.min()) * 0.1
    # Offset = (bottom of baseline) - (top of corrected) - (10% of original range)
    # This ensures corrected curve sits below baseline with visual separation
    fig.add_trace(go.Scatter(
        x=x,  # Same X values
        y=y_corrected + offset,  # Corrected intensity shifted down by offset
        mode='lines',  # Connected line (smooth corrected curve)
        name='Corrected (offset)',  # Legend shows this is offset for clarity
        line=dict(width=2, color='#2ca02c'),  # Green line, 2-pixel width
        hovertemplate=f'{x_label}: %{{x:.2f}}<br>Corrected: %{{y:.1f}}<extra></extra>'  # Custom tooltip
    ))

    # ========== CONFIGURE PLOT LAYOUT ==========
    # Set title, axis labels, styling, legend position
    fig.update_layout(
        title=title,  # Plot title (e.g., "Baseline Correction")
        xaxis_title=x_label,  # X-axis label
        yaxis_title="Intensity (a.u.)",  # Y-axis label
        hovermode='closest',  # Show hover tooltip for nearest point
        template='plotly_white',  # Clean white background
        height=500,  # Fixed height in pixels (taller than preview plot)
        showlegend=True,  # Display legend
        legend=dict(
            x=0.02,  # Position 2% from left (top-left corner)
            y=0.98,  # Position 98% from bottom
            bgcolor='rgba(255,255,255,0.8)'  # Semi-transparent white background
        )
    )

    # ========== APPLY WIDTH PRESET ==========
    # Apply user-selected width (Compact/Standard/Wide/Full)
    apply_plot_width(fig, width_preset)

    # ========== ADD X-RANGE INDICATORS (OPTIONAL) ==========
    # Add X-range markers if enabled (DEPRECATED in v2.2)
    if x_range_enabled and x_min is not None and x_max is not None:
        add_x_range_indicators(fig, x_min, x_max)

    return fig  # Return completed figure with 3 traces (original + baseline + corrected)


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
    # ========== CREATE SUBPLOT LAYOUT ==========
    # Create 2-row, 1-column subplot layout
    # Row 1 (75% height): Main plot with data, fit, and components
    # Row 2 (25% height): Residuals subplot
    # WHY: Residuals subplot helps evaluate fit quality (should be random noise around zero)
    fig = make_subplots(
        rows=2, cols=1,  # 2 rows, 1 column
        row_heights=[0.75, 0.25],  # Row 1 gets 75% of height, Row 2 gets 25%
        vertical_spacing=0.05,  # 5% gap between subplots
        subplot_titles=("Data & Fit", "Residuals")  # Titles for each subplot
    )

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

        # ==================== ROW 2: RESIDUALS SUBPLOT - DATA POINTS ====================
        # Add residuals (data - fit) to bottom subplot
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

        # ==================== ROW 2: RESIDUALS SUBPLOT - ZERO LINE ====================
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
    fig.update_xaxes(title_text=x_label, row=2, col=1)  # X-axis label only on bottom subplot
    fig.update_yaxes(title_text="Intensity (a.u.)", row=1, col=1)  # Y-axis label for main plot
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

    # ========== APPLY WIDTH PRESET ==========
    # Apply user-selected width (Compact/Standard/Wide/Full)
    apply_plot_width(fig, width_preset)

    # ========== ADD X-RANGE INDICATORS (OPTIONAL) ==========
    # Add X-range markers to main plot (row 1) if enabled
    # NOTE: DEPRECATED in v2.2 (data arrays cropped directly)
    if x_range_enabled and x_min is not None and x_max is not None:
        add_x_range_indicators(fig, x_min, x_max, row=1, col=1)  # Only add to row 1 (main plot)

    return fig  # Return completed figure with 2 subplots (data+fit+components, residuals)
