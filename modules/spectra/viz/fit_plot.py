"""
Static fit figures for export and reports.

Where live_plot.py renders the interactive, session-state-driven multi-layer
plot on the Analysis page, this module builds standalone figures with no
session-state dependencies: the data + fit + components view used for PNG/HTML
export and for the Sample Report's per-point grids.

Rendering these to the page goes through core.viz.render.render_plot().
"""

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Data and total-fit colors, named because a legend drawn outside these figures
# (the Sample Report draws one per slide) has to match the lines it describes.
DATA_COLOR = "#1f77b4"
FIT_COLOR = "#ff7f0e"

# A compact figure is rendered around 460px tall and then placed in a grid cell
# under 2 inches high, so one figure pixel is roughly a third of a point on the
# slide. Plotly's default 12px text arrives there at about 3.5pt — unreadable —
# which is why these look far too big for a figure and are not.
COMPACT_FONT_PX = 26
COMPACT_TITLE_PX = 34


def plot_composite(
    x: np.ndarray,
    y_data: np.ndarray,
    fit_result,  # FitResult object
    mode: str = "Raman",
    title: str = "Peak Fit Results",
    show_components: bool = True,
    show_residuals: bool = True,
    show_legend: bool = True,
    x_range: Optional[Tuple[float, float]] = None,
    y_range: Optional[Tuple[float, float]] = None,
    compact: bool = False,
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
    show_legend : bool, default=True
        Whether this figure draws its own legend. False where a set of these
        figures is shown together under one shared legend (the Sample
        Report's 3x3 grids), so it isn't repeated in every cell.
    x_range, y_range : Optional[Tuple[float, float]], default=None
        Explicit axis ranges. Passing the same ranges to every figure in a set
        is what makes their peak heights comparable by eye; None autoscales
        each figure independently. See `shared_axis_ranges`.
    compact : bool, default=False
        Strip the per-figure axis titles and shrink the margins and fonts, for
        figures rendered small in a grid where the slide labels the axes once.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Interactive Plotly figure with subplots.

    Notes
    -----
    Full implementation will be completed in Phase 5 (T042-T044).
    This is a simplified version for Phase 3 completion.
    """
    # Shrunk into a grid cell, default-weight lines and markers thin out to
    # near-invisible; these are the same shapes drawn heavier to survive it.
    marker_px = 5 if compact else 4
    fit_line_px = 3.0 if compact else 2
    component_line_px = 2.4 if compact else 1.5

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
        marker=dict(size=marker_px, color=DATA_COLOR),  # Blue dots
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
            line=dict(width=fit_line_px, color=FIT_COLOR),  # Orange line
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
                        # The peak's own color from its Material Preset, rather than
                        # Plotly's automatic cycling: the same peak then draws the same
                        # color in every point's plot, which is what lets one legend
                        # describe all nine of them.
                        line=dict(width=component_line_px, dash='dash', color=peak.color or None),
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
    # `compact` drops the axis titles entirely: the Sample Report tiles nine of
    # these into one slide and labels the axes once for the whole grid, so nine
    # copies of the same two labels would only shrink the spectra.
    if not compact:
        fig.update_xaxes(title_text=x_label, row=x_label_row, col=1)
        fig.update_yaxes(title_text="Intensity (a.u.)", row=1, col=1)  # Y-axis label for main plot
        if show_residuals:
            fig.update_yaxes(title_text="Residual", row=2, col=1)  # Y-axis label for residuals subplot

    # Explicit ranges put a whole set of figures on one scale; None leaves each
    # to autoscale, which is right for a figure viewed on its own.
    if x_range is not None:
        fig.update_xaxes(range=list(x_range))
    if y_range is not None:
        fig.update_yaxes(range=list(y_range), row=1, col=1)

    # ========== CONFIGURE OVERALL LAYOUT ==========
    # Set title, interactivity, styling, legend position for entire figure
    fig.update_layout(
        title=title,  # Overall plot title (e.g., "Peak Fit Results")
        hovermode='closest',  # Show hover tooltip for nearest point
        template='plotly_white',  # Clean white background with grid
        height=600,  # Total figure height in pixels (includes both subplots)
        showlegend=show_legend,
        legend=dict(
            x=1.02,  # Position just outside right edge of plot (2% beyond)
            y=1,  # Position at top (100% from bottom)
            bgcolor='rgba(255,255,255,0.8)'  # Semi-transparent white background
        )
    )

    if compact:
        # Hand the spectrum the pixels the legend, axis titles and default
        # margins were using. The left margin still has to fit the Y tick
        # labels, and the bottom the X ones.
        fig.update_layout(
            margin=dict(l=92, r=22, t=56, b=70),
            title=dict(text=title, x=0.5, xanchor="center", font=dict(size=COMPACT_TITLE_PX)),
            font=dict(size=COMPACT_FONT_PX),
        )
        # Fewer ticks than Plotly chooses for a figure this wide, so the
        # enlarged labels have room instead of colliding.
        fig.update_xaxes(nticks=6)
        fig.update_yaxes(nticks=5, row=1, col=1)

    return fig  # Return completed figure (data+fit+components, plus residuals if enabled)


def shared_axis_ranges(
    series: Iterable[Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]],
    pad: float = 0.05,
) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
    """
    One (x_range, y_range) pair covering every spectrum in `series`.

    Nine independently autoscaled plots can't be compared by eye — a weak point
    and a strong one both fill their frame. Plotting them all on these ranges
    makes the differences the thing you actually see.

    Parameters
    ----------
    series : iterable of (x, y_data, total_fit_curve)
        The fit curve may be None (an unfitted point still sets the range).
    pad : float, default=0.05
        Fraction of the Y span added at each end, so peaks don't touch the
        frame. X is left unpadded — its limits are the preset's crop range and
        are meaningful as they stand.

    Returns
    -------
    (x_range, y_range), or (None, None) if `series` yields nothing usable.
    """
    x_lo = y_lo = float("inf")
    x_hi = y_hi = float("-inf")

    for x, y_data, fit_curve in series:
        if x is None or len(x) == 0:
            continue
        x_lo, x_hi = min(x_lo, float(np.min(x))), max(x_hi, float(np.max(x)))
        for y in (y_data, fit_curve):
            if y is not None and len(y):
                y_lo, y_hi = min(y_lo, float(np.min(y))), max(y_hi, float(np.max(y)))

    if x_lo > x_hi or y_lo > y_hi:
        return None, None

    # A perfectly flat spectrum would give a zero-height range that Plotly
    # renders as a single line across the middle; give it something to show.
    span = y_hi - y_lo
    margin = span * pad if span > 0 else (abs(y_hi) * pad or 1.0)
    return (x_lo, x_hi), (y_lo - margin, y_hi + margin)


def fit_legend_entries(fit_results: Sequence) -> List[Tuple[str, str]]:
    """
    (label, hex color) for every trace this module draws, so one legend can be
    rendered outside the figures.

    Data and Total Fit first, then each distinct fitted peak in the order it is
    first seen across `fit_results` — taking the union rather than reading one
    fit, so a point that failed to resolve a peak doesn't drop it from the key.
    """
    entries = [("Data", DATA_COLOR), ("Total Fit", FIT_COLOR)]
    seen = set()

    for result in fit_results:
        if result is None or not getattr(result, "fitted_peaks", None):
            continue
        for i, peak in enumerate(result.fitted_peaks):
            label = peak.label or f"Peak {i + 1}"
            if label in seen:
                continue
            seen.add(label)
            entries.append((label, peak.color or DATA_COLOR))

    return entries
