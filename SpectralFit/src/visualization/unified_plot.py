"""
Unified plot rendering for all processing stages.

This module provides a single Plotly figure that displays multiple
toggleable layers: raw, de-spiked, baseline-corrected, fit results.

Key Functions:
--------------
- create_empty_figure(): Creates placeholder figure when no file loaded
- compute_default_visibility(): Determines which layers to show based on processing stage
- create_unified_figure(): Builds main Plotly figure with all data layers
- render_unified_plot(): Main entry point called from app.py (handles navigation + rendering)

Data Flow:
----------
1. User loads .txt file → raw_data (blue markers)
2. X-range cropping (optional) → crops raw_data arrays
3. De-spiking → processed_data (orange line)
4. Baseline correction → processed_data (purple line)
5. Peak fitting → fit_result (black line + colored components)

Each stage can show preview layers (red/orange dashed) before user clicks "Apply".

Layer Visibility Logic:
-----------------------
- Stage 1 (X-range): Only "Raw" visible
- Stage 2 (Despike): "Raw" + "De-spiked" visible (comparison)
- Stage 3 (Baseline): "De-spiked" + "Preview baseline" (red dashed)
- Stage 4 (Fit): "Baseline-corrected" + "Fit Total" + "Components" (optional)

User can override defaults via "View Options" checkboxes in control panel.
"""

# ==================== IMPORTS ====================
import plotly.graph_objects as go  # Plotly graphing library (creates interactive plots)
import streamlit as st  # Streamlit web framework (provides session_state, UI widgets)
from typing import Optional, Dict  # Type hints for function parameters/returns
from ..models.spectrum import SpectrumFile  # SpectrumFile dataclass (contains all spectrum data + metadata)


def create_empty_figure() -> go.Figure:
    """
    Create an empty placeholder figure.

    This function is called when no spectrum file is loaded yet.
    Shows a centered message "Load a file to view spectrum" instead of a blank plot.

    Returns
    -------
    go.Figure
        Empty Plotly figure with placeholder text and hidden axes.
    """
    # Create empty Plotly Figure object (no data traces)
    fig = go.Figure()

    # Add centered text annotation
    # xref="paper" and yref="paper" means coordinates are relative to plot area (0.0 to 1.0)
    # x=0.5, y=0.5 centers the text in the middle of the plot
    fig.add_annotation(
        text="Load a file to view spectrum",  # Message shown to user
        xref="paper",  # X reference: "paper" = plot area (not data coordinates)
        yref="paper",  # Y reference: "paper" = plot area
        x=0.5,  # X position: 0.5 = 50% from left (center horizontally)
        y=0.5,  # Y position: 0.5 = 50% from bottom (center vertically)
        showarrow=False,  # Don't show arrow pointing to annotation
        font=dict(size=20, color="gray")  # Large gray text for visibility
    )

    # Configure layout: hide axes (no data to show), set height, add margins
    fig.update_layout(
        xaxis=dict(visible=False),  # Hide X-axis (no gridlines, labels, or ticks)
        yaxis=dict(visible=False),  # Hide Y-axis
        height=600,  # Fixed height in pixels (matches data plot height)
        margin=dict(l=40, r=40, t=40, b=40)  # Margins: left, right, top, bottom (pixels)
    )

    return fig  # Return empty figure with placeholder text


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
    # Get status flags from spectrum object to determine processing stage
    # getattr() is used to safely access attributes that may not exist on older saved projects
    despike_done = getattr(spectrum, 'despike_done', False)  # True if despike was applied and confirmed
    baseline_done = getattr(spectrum, 'baseline_done', False)  # True if baseline correction was applied and confirmed
    fit_done = getattr(spectrum, 'fit_done', False)  # True if peak fitting was completed successfully

    # Check if previews are active (user is adjusting params)
    # Preview mode shows temporary results before user clicks "Apply"
    import streamlit as st
    # Despike preview exists when user adjusts threshold slider but hasn't clicked "Run De-spiking"
    despike_preview_active = ('despike_preview' in st.session_state and
                              st.session_state['despike_preview'] is not None)
    # Baseline preview exists when user adjusts baseline params but hasn't clicked "Run Baseline Correction"
    baseline_preview_active = ('baseline_preview' in st.session_state and
                               st.session_state['baseline_preview'] is not None)

    # Initialize all layer visibility flags to False (will be selectively enabled below)
    # This dictionary controls which plot layers are shown by default at each processing stage
    visibility = {
        "raw": False,  # Blue markers - original data as loaded from file
        "despiked": False,  # Orange line - data after cosmic ray removal (confirmed)
        "despiked_preview": False,  # Orange dashed - preview of despike effect (before confirmation)
        "baseline_preview": False,  # Red dashed - preview of baseline curve to be subtracted
        "corrected_preview": False,  # Reserved for future use (currently unused)
        "baseline_corrected": False,  # Purple line - data after baseline subtraction (confirmed)
        "fit_total": False,  # Black line - sum of all fitted peak components
        "components": False  # Colored dashed lines - individual Voigt peak components
    }

    # Apply visibility rules based on processing stage
    # Order matters: most advanced stage first, fallback to earlier stages
    if fit_done:
        # Skip previews when fit is already done
        # STAGE 4: After peak fitting completed successfully
        # Show final results: baseline-corrected data + fitted peaks
        visibility["raw"] = False  # Hide original raw data (not relevant for fit evaluation)
        visibility["despiked"] = False  # Hide intermediate processing layers
        visibility["baseline_corrected"] = True  # Purple line - data that was fitted
        visibility["fit_total"] = True  # Black line - sum of all fitted Voigt components
        visibility["components"] = False  # Hidden by default per design.md (user can enable in View Options)
        # WHY: User wants to see how well the fit matches the corrected data (R² evaluation)
    elif despike_preview_active:
        visibility["raw"] = True
        visibility["despiked_preview"] = False
        visibility["despiked"] = False
    elif baseline_preview_active:
        visibility["raw"] = True
        visibility["baseline_preview"] = True
        visibility["corrected_preview"] = True
        visibility["despiked"] = False
        visibility["baseline_corrected"] = False
    elif baseline_done:
        visibility["raw"] = False
        visibility["despiked"] = False
        visibility["baseline_corrected"] = True
        visibility["despiked_preview"] = False
    elif despike_done:
        # STAGE 2: After despike applied and confirmed (before baseline)
        # Show only the despiked data ready for baseline correction
        visibility["raw"] = False  # Hide original raw data with spikes
        visibility["despiked"] = True  # Orange line - spike-free spectrum
        # WHY: Spikes removed, now user can proceed to baseline correction
    # ELSE: Default visibility (all False) shows only raw data when first loaded

    return visibility  # Return dictionary mapping layer names to visibility booleans


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
    - "baseline_corrected": Final corrected (purple, line)
    - "fit_total": Fit total curve (black, line)
    - "component_N": Individual fit components (gray, dash)

    NOTE: "Preview Corrected" (green curve) was removed per user request.
    """
    # If no custom layer visibility provided, compute defaults based on processing stage
    if layer_config is None:
        layer_config = compute_default_visibility(spectrum)

    # Create empty Plotly Figure object - we'll add traces (data layers) to this
    fig = go.Figure()

    # Determine axis labels based on spectroscopy mode
    # Raman: X-axis is wavenumber shift from laser (cm⁻¹)
    # PL (Photoluminescence): X-axis is emission wavelength (nm)
    x_label = "Raman Shift (cm⁻¹)" if spectrum.mode == "Raman" else "Wavelength (nm)"
    y_label = "Intensity (a.u.)"  # Arbitrary units - not calibrated to absolute intensity

    # ==================== LAYER 1: RAW DATA ====================
    # Add raw data as first trace (always present - this is the original file data)
    # Uses markers (not line) to show discrete measurement points
    # Color: Blue (convention for raw/unprocessed data)
    fig.add_trace(go.Scatter(
        x=spectrum.raw_data.X,  # X values from original file (Raman shift or wavelength)
        y=spectrum.raw_data.Y,  # Y values from original file (intensity counts)
        mode="markers",  # Show as scatter points, not connected line
        name="Raw",  # Legend label
        marker=dict(size=3, color="blue"),  # Small blue dots
        visible=layer_config.get("raw", True)  # Visibility controlled by layer_config dict
    ))

    # ==================== LAYER 2: DE-SPIKED DATA (CONFIRMED) ====================
    # Only add this layer if despike processing was applied and confirmed
    despike_applied = spectrum.processing_settings.despike_applied  # Boolean flag set after "Run De-spiking"
    if despike_applied:
        # Add despiked data trace
        # Data source: spectrum.processed_data (modified Z-score algorithm removes cosmic ray spikes)
        # WHY: After despike, processed_data contains spike-free spectrum ready for baseline correction
        fig.add_trace(go.Scatter(
            x=spectrum.processed_data.X,  # X values same as raw (despike doesn't change X)
            y=spectrum.processed_data.Y,  # Y values with spikes removed/interpolated
            mode="lines",  # Use connected line (not markers) to show smooth corrected data
            name="De-spiked",  # Legend label
            line=dict(color="orange", width=2),  # Orange solid line (distinct from blue raw)
            visible=layer_config.get("despiked", False)  # Default hidden unless stage requires it
        ))

    # ==================== LAYER 2.5: DE-SPIKED PREVIEW (TEMPORARY) ====================
    # Only add if user is actively adjusting despike threshold slider (before clicking "Run")
    # Session state key 'despike_preview' is set by control_panel.py when slider changes
    if 'despike_preview' in st.session_state and st.session_state['despike_preview'] is not None:
        preview_data = st.session_state['despike_preview']  # Dict with 'x' and 'despiked' keys
        if 'despiked' in preview_data:
            # Add preview trace (dashed orange line to distinguish from confirmed despiked)
            # WHY: Real-time feedback - user sees spike removal effect before committing
            fig.add_trace(go.Scatter(
                x=preview_data['x'],  # X values from preview calculation
                y=preview_data['despiked'],  # Y values with preview threshold applied
                mode="lines",  # Connected line
                name="Preview De-spiked",  # Legend shows this is temporary preview
                line=dict(color="orange", width=2, dash="dash"),  # Dashed to indicate preview state
                visible=layer_config.get("despiked_preview", True)  # Show during preview stage
            ))

    # ==================== LAYER 3: BASELINE-CORRECTED DATA (CONFIRMED) ====================
    # Only add if baseline correction was applied and confirmed (user clicked "Run Baseline Correction")
    baseline_applied = spectrum.processing_settings.baseline_applied  # Boolean flag after baseline applied
    if baseline_applied:
        # Add baseline-corrected data trace
        # Data source: spectrum.processed_data (despiked data with baseline subtracted)
        # Baseline algorithms: Polynomial, ALS, Rolling Ball, Spline, or airPLS
        # WHY: After baseline removal, data is ready for peak fitting (background fluorescence removed)
        fig.add_trace(go.Scatter(
            x=spectrum.processed_data.X,  # X values unchanged by baseline correction
            y=spectrum.processed_data.Y,  # Y values with baseline subtracted (may have negative values)
            mode="markers",  # Connected line
            name="Baseline-corrected",  # Legend label
            line=dict(color="purple", width=1),  # Purple solid line (distinct from orange despiked)
            visible=layer_config.get("baseline_corrected", False)  # Hidden by default, shown after baseline stage
        ))

    # ==================== LAYER 4: BASELINE PREVIEW (TEMPORARY) ====================
    # Only add if user is actively adjusting baseline params (before clicking "Run")
    # Session state key 'baseline_preview' is set by control_panel.py when params change
    # NOTE: Removed "Preview Corrected" (green curve) per user request - now only show baseline curve
    if 'baseline_preview' in st.session_state and st.session_state['baseline_preview'] is not None:
        preview_data = st.session_state['baseline_preview']  # Dict with 'x', 'baseline' keys
        if 'baseline' in preview_data:
            # Add preview baseline trace (red dashed line showing what will be subtracted)
            # WHY: Real-time feedback - user sees if baseline follows background correctly before applying
            # This is the actual baseline curve, NOT the corrected data (user reviews baseline shape)
            fig.add_trace(go.Scatter(
                x=preview_data['x'],  # X values from preview calculation
                y=preview_data['baseline'],  # Y values of baseline curve (to be subtracted)
                mode="lines",  # Connected line
                name="Preview Baseline",  # Legend shows this is the baseline curve preview
                line=dict(color="red", width=2, dash="dash"),  # Red dashed (warning/preview color)
                visible=layer_config.get("baseline_preview", True)  # Show during baseline preview stage
            ))

    # ==================== LAYER 6: FIT TOTAL CURVE (CONFIRMED) ====================
    # Only add if peak fitting succeeded (Levenberg-Marquardt converged)
    # Check both that fit_result exists AND that fitting was successful
    if spectrum.fit_result is not None and spectrum.fit_result.success:
        # Also verify total_fit_curve was generated (should always exist if success=True)
        if hasattr(spectrum.fit_result, 'total_fit_curve') and spectrum.fit_result.total_fit_curve is not None:
            # Add fitted curve trace (sum of all Voigt peak components)
            # Data source: fit_result.total_fit_curve (calculated by lmfit after convergence)
            # This is the sum of all fitted Voigt peaks (Gaussian + Lorentzian convolution)
            # WHY: User compares this to baseline-corrected data to evaluate fit quality (R²)
            fig.add_trace(go.Scatter(
                x=spectrum.processed_data.X,  # Use same X as corrected data (fit domain)
                y=spectrum.fit_result.total_fit_curve,  # Y values from sum of all peak components
                mode="lines",  # Connected line
                name="Fit Total",  # Legend label
                line=dict(color="black", width=1.5,dash="dash"),  # Black solid line (standard for fit total)
                visible=layer_config.get("fit_total", False)  # Hidden until fit stage
            ))

    # ==================== LAYERS 7+: FIT COMPONENTS (INDIVIDUAL PEAKS) ====================
    # Only add if fitting succeeded AND user enabled "Show Components" checkbox
    # Each fitted peak gets its own trace (e.g., D-band, G-band for Raman)
    if spectrum.fit_result is not None and spectrum.fit_result.success:
        # Check that fitted_peaks list exists and is not empty
        if hasattr(spectrum.fit_result, 'fitted_peaks') and spectrum.fit_result.fitted_peaks:
            # Only add component traces if user explicitly enabled them (hidden by default per design.md)
            if layer_config.get("components", False):
                # Loop through each fitted peak and add its component curve
                for i, peak in enumerate(spectrum.fit_result.fitted_peaks):
                    # Verify component_curve was generated for this peak
                    if hasattr(peak, 'component_curve') and peak.component_curve is not None:
                        # Get peak label (e.g., "D-band", "G-band") or default to "Peak 1", "Peak 2"
                        peak_label = getattr(peak, 'label', f"Peak {i+1}")
                        # Get peak color from user-defined color (set in peak table or auto-assigned)
                        peak_color = getattr(peak, 'color', "#1f77b4")  # Default to blue if missing
                        # Add individual peak component trace
                        # WHY: User can see contribution of each peak to total fit (e.g., D vs G-band ratio)
                        fig.add_trace(go.Scatter(
                            x=spectrum.processed_data.X,  # Same X as fit total
                            y=peak.component_curve,  # Y values for this single Voigt peak
                            mode="lines",  # Connected line
                            name=peak_label,  # Legend shows peak label (e.g., "D-band")
                            line=dict(color=peak_color, width=2.5),  # Dashed thinner line
                            opacity=0.7,  # Semi-transparent to avoid cluttering plot
                            visible=True  # Always visible when components layer is enabled
                        ))

    # ==================== LAYER 7.5: RESIDUALS (FIT QUALITY INDICATOR) ====================
    # Only add if fitting succeeded AND user enabled "Show Residuals" checkbox
    # Residuals = Baseline-corrected - Fit Total (should be random noise around zero)
    # WHY: Residuals show fit quality - patterns indicate systematic errors (e.g., missing peaks)
    if spectrum.fit_result is not None and spectrum.fit_result.success:
        # Check that residuals array exists (calculated by lmfit)
        if hasattr(spectrum.fit_result, 'residuals') and spectrum.fit_result.residuals is not None:
            # Only add residuals if user explicitly enabled them
            if layer_config.get("residuals", False):
                # Add residuals trace as scatter plot (not line - want to see discrete residual points)
                # Color: Green (distinct from other layers)
                # WHY: User evaluates fit quality - residuals should be random noise around zero
                import numpy as np
                fig.add_trace(go.Scatter(
                    x=spectrum.processed_data.X,  # Same X as fit
                    y=spectrum.fit_result.residuals,  # Y = corrected - fit (from lmfit)
                    mode="markers",  # Scatter points (not line)
                    name="Residuals",  # Legend label
                    marker=dict(size=3, color="green"),  # Small green dots
                    visible=True  # Always visible when residuals layer is enabled
                ))

    # ==================== LAYERS 8+: PEAK MARKERS (INITIAL GUESSES) ====================
    # Only add if user has defined peaks in peak table AND enabled "Show Peak Markers"
    # These are vertical lines showing user's initial peak guesses (before fitting)
    # WHY: User can see where they defined peaks relative to the data (useful for troubleshooting fits)
    if len(spectrum.peak_table) > 0 and layer_config.get("show_peak_markers", False):
        # Determine which Y data to use for marker heights (depends on processing stage)
        # We want markers to reach the current data curve height
        if spectrum.baseline_done:
            # After baseline: use baseline-corrected data height
            Y_ref = spectrum.processed_data.Y
        elif spectrum.despike_done:
            # After despike: use despiked data height
            Y_ref = spectrum.processed_data.Y
        else:
            # Before any processing: use raw data height
            Y_ref = spectrum.raw_data.Y

        # Also get corresponding X data (in case despike modified it)
        X_ref = spectrum.processed_data.X if spectrum.despike_done else spectrum.raw_data.X

        # Loop through each peak in peak_table (PeakDefinition objects)
        for peak in spectrum.peak_table:
            # Find Y value at peak center position
            # Use argmin to find index of X value closest to peak.center
            idx = np.argmin(np.abs(X_ref - peak.center))
            y_at_peak = Y_ref[idx] if idx < len(Y_ref) else 0  # Safeguard against index error

            # Add vertical line marker from Y=0 to Y=peak_height
            # WHY: Shows peak position visually on plot
            fig.add_trace(go.Scatter(
                x=[peak.center, peak.center],  # Two points: (center, 0) and (center, y_at_peak)
                y=[0, y_at_peak],  # Vertical line from baseline to peak
                mode='lines',  # Line mode (not markers)
                name=f"{peak.label} (initial)",  # Legend shows this is initial guess
                line=dict(color=peak.color, width=1.5, dash='dot'),  # Dotted line (distinct from fit components)
                showlegend=True,  # Show in legend
                visible=True  # Always visible when peak markers layer enabled
            ))

            # Add diamond marker at peak center
            # WHY: Highlights exact peak center position
            fig.add_trace(go.Scatter(
                x=[peak.center],  # Single point at peak center
                y=[y_at_peak],  # At data height
                mode='markers',  # Marker mode (not line)
                name=peak.label,  # Legend label
                marker=dict(color=peak.color, size=8, symbol='diamond'),  # Diamond shape
                showlegend=False,  # Don't duplicate legend entry (already shown by vertical line)
                visible=True  # Always visible when peak markers layer enabled
            ))

    # ==================== NOTE: X-RANGE INDICATORS REMOVED ====================
    # In v2.2, we crop the data arrays directly instead of showing indicators on plot
    # This simplifies visualization - data outside X-range is simply not present in arrays

    # ==================== CONFIGURE PLOT LAYOUT ====================
    # Set axis labels, sizing, interactivity, legend position, margins
    fig.update_layout(
        xaxis_title=x_label,  # "Raman Shift (cm⁻¹)" or "Wavelength (nm)"
        yaxis_title=y_label,  # "Intensity (a.u.)"
        height=600,  # Fixed plot height in pixels (fits nicely in 70% center column)
        hovermode="closest",  # Hover shows nearest data point info (X, Y values)
        template="plotly_white",  # Clean white background with light grid lines
        legend=dict(
            yanchor="top",  # Anchor legend at its top edge
            y=0.99,  # Position 99% from bottom (nearly at top of plot)
            xanchor="right",  # Anchor legend at its right edge
            x=0.99,  # Position 99% from left (nearly at right edge of plot)
            bgcolor="rgba(255,255,255,0.8)"  # Semi-transparent white background (so data visible behind)
        ),
        margin=dict(l=60, r=40, t=40, b=60)  # Left/right/top/bottom margins (pixels) - room for axis labels
    )

    return fig  # Return completed Plotly Figure object


def render_unified_plot():
    """
    Render the unified plot in the center panel.

    This function is called from app.py within the center column (70% width).
    Handles file navigation UI and plot rendering.
    """
    # ==================== FILE NAVIGATION UI ====================
    # Get files dict and current_file from Streamlit session state
    # Session state persists across Streamlit reruns (like global variables)
    files = st.session_state.get("files", {})  # Dict mapping filename -> SpectrumFile object
    current_file = st.session_state.get("current_file")  # Currently selected filename (string)

    # Only show navigation if files were loaded
    if files:
        file_list = list(files.keys())  # Convert dict keys to list for indexing

        # Resolve current index
        current_idx = file_list.index(current_file) if current_file in file_list else 0

        def _update_visibility_for_file(spectrum):
            """Update plot visibility settings based on file's processing state."""
            # Clear preview data to prevent stale previews from previous file
            st.session_state['despike_preview'] = None
            st.session_state['baseline_preview'] = None
            if spectrum.fit_done and getattr(spectrum, 'fit_result', None) and spectrum.fit_result.success:
                st.session_state['show_raw'] = False
                st.session_state['show_despiked'] = False
                st.session_state['show_corrected'] = True
                st.session_state['show_fit'] = True
                st.session_state['show_components'] = True
                st.session_state['show_residuals'] = True
            elif getattr(spectrum, 'baseline_done', False):
                st.session_state['show_raw'] = False
                st.session_state['show_despiked'] = False
                st.session_state['show_corrected'] = True
                st.session_state['show_fit'] = False
                st.session_state['show_components'] = False
                st.session_state['show_residuals'] = False
            else:
                st.session_state['show_raw'] = True
                st.session_state['show_despiked'] = False
                st.session_state['show_corrected'] = False
                st.session_state['show_fit'] = False
                st.session_state['show_components'] = False
                st.session_state['show_residuals'] = False

        # Handle arrow button clicks from previous rerun
        nav_action = st.session_state.pop('_file_nav_action', None)
        if nav_action == 'prev':
            current_idx = (current_idx - 1) % len(file_list)
            st.session_state['current_file'] = file_list[current_idx]
            current_file = file_list[current_idx]
            _update_visibility_for_file(files[current_file])
        elif nav_action == 'next':
            current_idx = (current_idx + 1) % len(file_list)
            st.session_state['current_file'] = file_list[current_idx]
            current_file = file_list[current_idx]
            _update_visibility_for_file(files[current_file])

        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 6, 1, 1])

        with nav_col1:
            if st.button("◀", key="file_prev", help="Previous file"):
                st.session_state['_file_nav_action'] = 'prev'
                st.rerun()

        with nav_col2:
            # Use return value instead of key+callback to avoid widget state conflicts
            selected = st.selectbox(
                "File",
                options=file_list,
                index=current_idx,
                label_visibility="collapsed"
            )
            if selected != current_file:
                st.session_state['current_file'] = selected
                current_file = selected
                current_idx = file_list.index(selected)
                _update_visibility_for_file(files[current_file])

        with nav_col3:
            if st.button("▶", key="file_next", help="Next file"):
                st.session_state['_file_nav_action'] = 'next'
                st.rerun()

        with nav_col4:
            st.markdown(
                f"<div style='text-align: center; padding-top: 8px; color: #666;'>{current_idx + 1}/{len(file_list)}</div>",
                unsafe_allow_html=True
            )

    # ==================== GET CURRENT SPECTRUM ====================
    # Retrieve SpectrumFile object for currently selected file
    spectrum = files.get(current_file)  # Returns None if current_file not in files dict

    # ==================== CREATE PLOT FIGURE ====================
    if spectrum is None:
        # No file selected yet - show empty placeholder figure
        fig = create_empty_figure()
    else:
        # File loaded - create unified figure with all data layers
        # Get layer visibility from View Options checkboxes in control panel
        # These session state keys are set by checkboxes in control_panel.py
        layer_config = {
            "raw": st.session_state.get("show_raw", True),  # Default: show raw data
            "despiked": st.session_state.get("show_despiked", False),  # Default: hide despiked
            "baseline_corrected": st.session_state.get("show_corrected", False),  # Default: hide corrected
            "fit_total": st.session_state.get("show_fit", False),  # Default: hide fit
            "components": st.session_state.get("show_components", False),  # Default: hide components
            "residuals": st.session_state.get("show_residuals", False)  # Default: hide residuals
        }

        # Call create_unified_figure() to build Plotly figure with all layers
        fig = create_unified_figure(spectrum, layer_config)

    # ==================== RENDER PLOT ====================
    # Add HTML anchor for mobile "Jump to Plot" link (allows mobile users to skip controls)
    st.markdown('<div id="plot-anchor"></div>', unsafe_allow_html=True)

    # Render Plotly figure using Streamlit's plotly_chart widget
    # use_container_width=True makes plot fill the 70% center column width
    # key="unified_plot" gives this widget a unique identifier for Streamlit state
    st.plotly_chart(fig, use_container_width=True, key="unified_plot")
