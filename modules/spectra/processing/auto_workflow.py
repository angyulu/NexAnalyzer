"""
Automated workflow execution engine.

This module orchestrates the complete processing pipeline:
X-range → De-spike → Baseline → Peak Fitting
"""

import streamlit as st
import numpy as np
from typing import Dict, Any
from ..models.spectrum import SpectrumFile, SpectrumData
from ..models.preset import MaterialPreset, parse_exclusion_ranges
from .despiking import remove_spikes
from .baseline import (
    baseline_polynomial_with_autoshift,
    baseline_als_with_autoshift,
    baseline_polynomial_with_mask,
    baseline_als_with_mask
)
from .fitting import fit_voigt_peaks
from ..utils.fit_staleness import mark_fit_stale_if_needed, compute_preprocessing_hash


class WorkflowExecutionError(Exception):
    """Custom exception for workflow execution failures."""
    pass


def execute_auto_workflow(
    spectrum: SpectrumFile,
    preset: MaterialPreset,
    max_iterations: int = 2000
) -> Dict[str, Any]:
    """
    Execute full automated workflow using preset.

    Pipeline: X-range → Despike → Baseline → Fitting

    Parameters
    ----------
    spectrum : SpectrumFile
        Current spectrum file to process
    preset : MaterialPreset
        Preset configuration

    Returns
    -------
    result : dict
        Execution results with keys:
        - success: bool
        - stage_completed: str (last completed stage)
        - error_message: str (if success=False)
        - fit_result: FitResult (if success=True)

    Notes
    -----
    Modifies spectrum object in-place. Stages before failure remain completed.
    """
    result = {
        "success": False,
        "stage_completed": None,
        "error_message": "",
        "fit_result": None
    }

    try:
        # Sync spectrum mode from preset (axis labels, center tolerance,
        # PL-only Raw row in Fit Results). Defensive: callers may pass
        # spectra with stale modes (e.g. batch path).
        if spectrum.mode != preset.mode:
            spectrum.mode = preset.mode

        # ========== STAGE 1: X-RANGE CROPPING ==========
        # Match manual workflow: replicate what happens when user clicks "Apply X-Range"
        if preset.x_range_enabled:
            # Use raw_data as source (NOT original_data - matches manual workflow)
            X_raw = spectrum.raw_data.X
            Y_raw = spectrum.raw_data.Y

            # Apply mask
            mask = (X_raw >= preset.x_min) & (X_raw <= preset.x_max)
            if not np.any(mask):
                raise WorkflowExecutionError(
                    f"No data in X-range [{preset.x_min}, {preset.x_max}]. "
                    f"File range: [{X_raw.min():.1f}, {X_raw.max():.1f}]. "
                    f"Suggestion: Adjust x_min/x_max in preset to match your data."
                )

            X_cropped = X_raw[mask]
            Y_cropped = Y_raw[mask]

            # Update BOTH raw_data and processed_data (matches manual workflow)
            spectrum.raw_data = SpectrumData(X=X_cropped, Y=Y_cropped)
            spectrum.processed_data = SpectrumData(X=X_cropped, Y=Y_cropped)

            # Reset X-range flags (matches manual workflow)
            spectrum.x_range_enabled = False
            spectrum.x_min = None
            spectrum.x_max = None

            # Reset downstream flags (matches manual workflow)
            spectrum.despike_done = False
            spectrum.baseline_done = False
            spectrum.fit_done = False
            spectrum.processing_settings.despike_applied = False
            spectrum.processing_settings.baseline_applied = False

            # Clear preview states (matches manual workflow)
            if 'despike_preview' in st.session_state:
                st.session_state['despike_preview'] = None
            if 'baseline_preview' in st.session_state:
                st.session_state['baseline_preview'] = None

            # Update view options (matches manual workflow)
            st.session_state['show_raw'] = True
            st.session_state['show_despiked'] = False
            st.session_state['show_corrected'] = False
            st.session_state['show_fit'] = False
            st.session_state['show_components'] = False

            # Auto-expand next section (matches manual workflow)
            st.session_state['expanded_section'] = 'despiking'

        result["stage_completed"] = "x_range"

        # ========== STAGE 2: DE-SPIKING ==========
        # Match manual workflow: replicate what happens when user clicks "Run Despike"
        X = spectrum.processed_data.X
        Y = spectrum.processed_data.Y

        # Save threshold to settings (matches manual workflow)
        spectrum.processing_settings.despike_threshold = preset.despike_threshold

        # Run despike algorithm and unpack tuple (matches manual workflow)
        Y_despiked, spike_mask = remove_spikes(Y, threshold=preset.despike_threshold)

        # Update processed_data (X unchanged, Y updated - matches manual workflow)
        spectrum.processed_data = SpectrumData(X=X, Y=Y_despiked)

        # Set flags (matches manual workflow)
        spectrum.processing_settings.despike_applied = True
        spectrum.despike_done = True

        # Mark fit as stale if it exists (matches manual workflow)
        mark_fit_stale_if_needed(spectrum)

        # Clear preview state (matches manual workflow)
        if 'despike_preview' in st.session_state:
            st.session_state['despike_preview'] = None

        # Update view options (matches manual workflow)
        st.session_state['show_raw'] = True
        st.session_state['show_despiked'] = True  # Show despiked for comparison
        st.session_state['show_corrected'] = False
        st.session_state['show_fit'] = False
        st.session_state['show_components'] = False

        # Auto-expand next section (matches manual workflow)
        st.session_state['expanded_section'] = 'baseline'

        result["stage_completed"] = "despike"

        # ========== STAGE 3: BASELINE CORRECTION ==========
        # Match manual workflow: replicate what happens when user clicks "Run Baseline Correction"
        result["stage_completed"] = "baseline"

        if preset.baseline_algorithm == "None (Skip)":
            # Skip baseline, mark as done
            spectrum.processing_settings.baseline_applied = False
            spectrum.baseline_done = True
        else:
            X = spectrum.processed_data.X
            Y_despiked = spectrum.processed_data.Y

            # Parse exclusion ranges if provided
            exclusions = None
            if preset.exclusion_ranges:
                try:
                    exclusions = parse_exclusion_ranges(preset.exclusion_ranges)
                except ValueError as e:
                    raise WorkflowExecutionError(
                        f"Invalid exclusion_ranges format: {e}. "
                        f"Expected format: '1200-1400; 2600-2800'"
                    )

            # Route to appropriate algorithm (matches manual workflow)
            if preset.baseline_algorithm == "Polynomial":
                if exclusions:
                    # Use masked version (no autoshift)
                    Y_corrected, baseline_curve = baseline_polynomial_with_mask(
                        X, Y_despiked,
                        degree=preset.baseline_degree,
                        exclusions=exclusions
                    )
                    y_shift = 0.0  # No shift in masked version
                else:
                    # Use standard version with autoshift
                    Y_corrected, baseline_curve, y_shift = baseline_polynomial_with_autoshift(
                        X, Y_despiked, degree=preset.baseline_degree
                    )
            elif preset.baseline_algorithm == "ALS":
                if exclusions:
                    # Use masked version (no autoshift)
                    Y_corrected, baseline_curve = baseline_als_with_mask(
                        X, Y_despiked,
                        lambda_=preset.baseline_lambda,
                        p=preset.baseline_p,
                        exclusions=exclusions
                    )
                    y_shift = 0.0  # No shift in masked version
                else:
                    # Use standard version with autoshift
                    Y_corrected, baseline_curve, y_shift = baseline_als_with_autoshift(
                        X, Y_despiked,
                        lambda_=preset.baseline_lambda,
                        p=preset.baseline_p
                    )
            else:
                raise WorkflowExecutionError(
                    f"Baseline algorithm '{preset.baseline_algorithm}' not supported. "
                    f"Supported: 'Polynomial', 'ALS', 'None (Skip)'. "
                    f"Suggestion: Check baseline_algorithm spelling in preset."
                )

            # Update processing_settings (matches manual workflow)
            spectrum.processing_settings.baseline_algorithm = preset.baseline_algorithm
            if preset.baseline_algorithm == "Polynomial":
                spectrum.processing_settings.baseline_degree = preset.baseline_degree if preset.baseline_degree else 3
            else:  # ALS
                spectrum.processing_settings.baseline_lambda = preset.baseline_lambda if preset.baseline_lambda else 10000.0
                spectrum.processing_settings.baseline_p = preset.baseline_p if preset.baseline_p else 0.001

            # Save Y-shift amount (matches manual workflow)
            spectrum.processing_settings.y_shift = y_shift

            # Update processed_data (matches manual workflow)
            spectrum.processed_data = SpectrumData(X=X, Y=Y_corrected)

            # Set flags (matches manual workflow)
            spectrum.processing_settings.baseline_applied = True
            spectrum.baseline_done = True

            # Mark fit as stale if it exists (matches manual workflow)
            mark_fit_stale_if_needed(spectrum)

            # Clear preview state (matches manual workflow)
            if 'baseline_preview' in st.session_state:
                st.session_state['baseline_preview'] = None

        # Update view options (matches manual workflow)
        st.session_state['show_raw'] = False
        st.session_state['show_despiked'] = False
        st.session_state['show_corrected'] = True  # Show baseline-corrected
        st.session_state['show_fit'] = False
        st.session_state['show_components'] = False

        # Auto-expand next section (matches manual workflow)
        st.session_state['expanded_section'] = 'peak_fitting'

        # ========== STAGE 4: PEAK FITTING ==========
        # Match manual workflow: replicate what happens when user clicks "Run Voigt Fit"
        X = spectrum.processed_data.X
        Y_corrected = spectrum.processed_data.Y

        # Convert peak templates to PeakDefinitions (matches manual workflow)
        x_range = (X.min(), X.max())
        y_max = Y_corrected.max()
        spectral_resolution = np.median(np.abs(np.diff(X)))

        peak_definitions = []
        for template in preset.peak_templates:
            try:
                peak_def = template.to_peak_definition(
                    mode=preset.mode,
                    x_range=x_range,
                    y_max=y_max,
                    spectral_resolution=spectral_resolution
                )
                peak_definitions.append(peak_def)
            except Exception as e:
                raise WorkflowExecutionError(
                    f"Failed to convert peak template '{template.peak_label}': {e}"
                )

        # Update spectrum peak table (matches manual workflow)
        spectrum.peak_table = peak_definitions

        # Execute fitting (matches manual workflow)
        try:
            fit_result = fit_voigt_peaks(
                X, Y_corrected, peak_definitions,
                mode=preset.mode, max_iterations=max_iterations
            )
        except Exception as e:
            raise WorkflowExecutionError(
                f"Peak fitting failed: {e}. "
                f"Suggestion: Check peak initial guesses (center, amplitude, width) in preset."
            )

        if not fit_result.success:
            raise WorkflowExecutionError(
                f"Peak fitting did not converge: {fit_result.error_message}. "
                f"Suggestion: Adjust peak centers or tolerances in preset."
            )

        # Save result (matches manual workflow)
        spectrum.fit_result = fit_result

        # Set flags (matches manual workflow)
        spectrum.fit_done = True
        spectrum.fit_stale = False

        # Compute and save preprocessing hash (matches manual workflow)
        spectrum.last_preprocessing_hash = compute_preprocessing_hash(spectrum)

        # Clear preview states (matches manual workflow)
        if 'despike_preview' in st.session_state:
            st.session_state['despike_preview'] = None
        if 'baseline_preview' in st.session_state:
            st.session_state['baseline_preview'] = None

        # Update view options (matches manual workflow)
        st.session_state['show_raw'] = False
        st.session_state['show_despiked'] = False
        st.session_state['show_corrected'] = True       # Show baseline-corrected data
        st.session_state['show_fit'] = True             # Show fit total curve
        st.session_state['show_components'] = True      # Show peak components
        st.session_state['show_residuals'] = True       # Show residuals

        # Auto-expand export section (matches manual workflow)
        st.session_state['expanded_section'] = 'export'

        result["stage_completed"] = "fitting"
        result["fit_result"] = fit_result
        result["success"] = True

        return result

    except WorkflowExecutionError as e:
        result["error_message"] = str(e)
        return result
    except Exception as e:
        result["error_message"] = f"Unexpected error at stage '{result['stage_completed']}': {str(e)}"
        return result


def format_workflow_summary(result: Dict[str, Any], preset: MaterialPreset) -> str:
    """
    Format workflow execution result as user-friendly summary.

    Parameters
    ----------
    result : dict
        Result from execute_auto_workflow()
    preset : MaterialPreset
        Preset that was used

    Returns
    -------
    str
        Formatted summary message
    """
    if result["success"]:
        fit_result = result["fit_result"]
        summary = (
            f"**Auto-workflow completed successfully!**\n\n"
            f"**Material:** {preset.material_name} ({preset.mode})\n"
            f"**Stages:**\n"
            f"- X-range: {'Applied' if preset.x_range_enabled else 'Skipped'}"
        )
        if preset.x_range_enabled:
            summary += f" ({preset.x_min} - {preset.x_max})"
        summary += (
            f"\n- De-spiking: Threshold {preset.despike_threshold}\n"
            f"- Baseline: {preset.baseline_algorithm}\n"
            f"- Fitting: {len(preset.peak_templates)} peaks fitted\n\n"
            f"**Fit Quality:**\n"
            f"- R²: {fit_result.r_squared:.4f}\n"
            f"- χ²: {fit_result.chi_squared:.2e}\n"
            f"- Convergence time: {fit_result.convergence_time:.2f}s"
        )
        return summary
    else:
        return (
            f"**Auto-workflow failed at stage: {result['stage_completed']}**\n\n"
            f"{result['error_message']}"
        )


def get_workflow_suggestions(stage: str, error_msg: str) -> str:
    """
    Provide helpful suggestions based on failure stage and error.

    Parameters
    ----------
    stage : str
        Stage that failed
    error_msg : str
        Error message

    Returns
    -------
    str
        Suggestion text
    """
    suggestions = {
        "x_range": (
            "**Common fixes:**\n"
            "- Open Excel file and adjust x_min/x_max to match your data range\n"
            "- Or disable x_range_enabled in preset\n"
            "- Check that your file units match preset mode (cm⁻¹ for Raman, nm for PL)"
        ),
        "despike": (
            "**Common fixes:**\n"
            "- Increase despike_threshold (try 8.0-10.0 for noisy data)\n"
            "- Or decrease threshold (try 3.0-5.0) if removing too many points"
        ),
        "baseline": (
            "**Common fixes:**\n"
            "- Try different baseline algorithm (Polynomial vs ALS)\n"
            "- For Polynomial: Adjust baseline_degree (typically 2-5)\n"
            "- For ALS: Adjust baseline_lambda (higher = smoother, try 50000-100000)\n"
            "- For ALS: Adjust baseline_p (lower = more asymmetric, try 0.01-0.05)"
        ),
        "fitting": (
            "**Common fixes:**\n"
            "- Check peak centers match your spectrum (view data first)\n"
            "- Increase center_tolerance to allow more fitting flexibility\n"
            "- Adjust initial amplitude guesses (should be ~peak height)\n"
            "- Reduce number of peaks if spectrum is simple\n"
            "- Try manual workflow to see if baseline correction is adequate"
        )
    }

    return suggestions.get(stage, "Try manual workflow to diagnose the issue.")
