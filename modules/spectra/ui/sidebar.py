"""
Sidebar UI component for the Analysis page: mode selection, file upload,
and results export.

This module provides the render_sidebar() function that displays, in order:
- Material Presets: a dropdown sourced from src/presets/materials.json
  (edited on the "Material Presets" page — see pages/material_presets.py)
  plus the Run Auto-Workflow / Run All Files buttons
- Quick Export (PNG/HTML/CSV) and Batch Export (master CSV)
- Reset to Raw
- Load Spectra (file upload widget) and Loaded Files (file selector)
- View Options (plot layer visibility), last in the sidebar
"""

import streamlit as st
from ..models.spectrum import SpectrumFile, ProcessingSettings
from ..processing.parser import parse_spectrum_multi, detect_mode_from_filename
from core.io.export import (
    export_figure_png,
    export_figure_html,
    create_filename,
    prompt_save_path,
)
from ..io.results_csv import export_fit_params_csv, export_master_csv
from ..io.preset_store import load_presets
from ..viz.fit_plot import plot_composite
from .session_state import (
    initialize_session_state,
    add_spectrum_file,
    remove_spectrum_file,
    clear_all_files,
    set_mode,
    get_current_spectrum,
)


def render_sidebar():
    """
    Render sidebar with mode toggle, file upload, and results export.

    This function should be called from app.py within a `with st.sidebar:` block.

    Notes
    -----
    - Mode toggle affects axis labels and fitting bounds
    - File upload supports multiple files (batch loading)
    - File selector dropdown shows all loaded files
    """
    # Initialize session state
    initialize_session_state()

    st.header("Settings")

    # Material Presets (embedded/JSON-backed as of v2.11.0 — add or edit
    # materials on the "Material Presets" page; preset.mode drives spectrum.mode below)
    st.subheader("Material Presets")

    presets = load_presets()
    files = st.session_state.get("files", {})
    current_file = st.session_state.get("current_file")
    current_spectrum = files[current_file] if (files and current_file) else None

    if presets:
        preset_keys = sorted(key for key, p in presets.items() if p.enabled)

        selected_key = st.selectbox(
            "Select Material",
            options=[None] + preset_keys,
            index=0,
            format_func=lambda k: "(None)" if k is None else f"{k[0]} ({k[1]})",
            help="Materials configured on the Material Presets page (Raman + PL)"
        )

        if selected_key is not None:
            preset = presets[selected_key]
            st.session_state['selected_preset'] = preset

            # Sync mode on all loaded files (drives axis labels, tolerance, and the
            # PL-only Raw row in the Fit Results table). Without this, files other
            # than the current one keep their load-time mode after "Run All Files".
            for _spec in files.values():
                if _spec.mode != preset.mode:
                    _spec.mode = preset.mode

            # Display preset info
            st.caption(f"**Mode**: {preset.mode}")
            st.caption(f"**Baseline**: {preset.baseline_algorithm}")
            st.caption(f"**Peaks**: {len(preset.peak_templates)}")
            if preset.description:
                st.caption(f"**Notes**: {preset.description}")

            if current_spectrum is None:
                st.caption("Load spectrum files below to enable Auto-Workflow")

            # Max iterations slider — applies to Run Auto-Workflow and Run All Files
            # (shared with the manual fit slider in the Peak Fitting control panel)
            max_iter_sidebar = st.slider(
                "Max iterations",
                min_value=500, max_value=20000,
                value=st.session_state.get("max_iterations", 2000),
                step=500,
                key="max_iter_sidebar_slider",
                help="Higher = more attempts to converge for difficult fits"
            )
            st.session_state["max_iterations"] = max_iter_sidebar

            # Run Auto-Workflow button (requires a loaded file)
            run_clicked = st.button(
                "🚀 Run Auto-Workflow", type="primary", use_container_width=True,
                disabled=current_spectrum is None
            )
            if run_clicked and current_spectrum is not None:
                # Execute auto-workflow immediately (single-click behavior)
                from ..processing.auto_workflow import execute_auto_workflow, format_workflow_summary, get_workflow_suggestions

                max_iter = st.session_state.get("max_iterations", 2000)
                with st.spinner("🚀 Executing automated workflow..."):
                    result = execute_auto_workflow(current_spectrum, preset, max_iterations=max_iter)

                if result["success"]:
                    # Show success message with summary
                    summary = format_workflow_summary(result, preset)
                    st.success(summary)

                    # Update view options to show fit results
                    st.session_state['show_fit'] = True
                    st.session_state['show_components'] = True

                    # Auto-expand export section
                    st.session_state['expanded_section'] = 'export'

                else:
                    # Show error message with suggestions
                    st.error(format_workflow_summary(result, preset))

                    # Show contextual suggestions
                    if result['stage_completed']:
                        suggestions = get_workflow_suggestions(
                            result['stage_completed'],
                            result['error_message']
                        )
                        st.info(suggestions)

                    # Expand section where failure occurred
                    stage_to_section = {
                        'x_range': 'processing_range',
                        'despike': 'despiking',
                        'baseline': 'baseline',
                        'fitting': 'peak_fitting'
                    }
                    failed_section = stage_to_section.get(result['stage_completed'], 'processing_range')
                    st.session_state['expanded_section'] = failed_section

                # Trigger rerun to update UI
                st.rerun()

            # Batch auto-workflow button (only if multiple files loaded)
            if len(files) > 1:
                if st.button("🚀 Run All Files", type="secondary", use_container_width=True,
                             help="Run auto-workflow on all loaded files"):
                    from ..processing.auto_workflow import execute_auto_workflow, format_workflow_summary

                    file_items = list(files.items())
                    total = len(file_items)
                    success_count = 0
                    failed_files = []

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    max_iter = st.session_state.get("max_iterations", 2000)
                    for idx, (filename, spectrum) in enumerate(file_items):
                        status_text.text(f"Processing {idx + 1}/{total}: {filename}")
                        progress_bar.progress((idx + 1) / total)

                        result = execute_auto_workflow(spectrum, preset, max_iterations=max_iter)
                        if result["success"]:
                            success_count += 1
                        else:
                            failed_files.append((filename, result.get("error_message", "Unknown error")))

                    progress_bar.empty()
                    status_text.empty()

                    if success_count == total:
                        st.success(f"All {total} files processed successfully!")
                    elif success_count > 0:
                        st.warning(f"{success_count}/{total} files succeeded. {len(failed_files)} failed.")
                    else:
                        st.error("All files failed processing.")

                    if failed_files:
                        with st.expander("View Errors"):
                            for fname, err in failed_files:
                                st.error(f"**{fname}**: {err}")

                    st.session_state['show_fit'] = True
                    st.session_state['show_components'] = True
                    st.session_state['expanded_section'] = 'export'
                    st.session_state['despike_preview'] = None
                    st.session_state['baseline_preview'] = None
                    st.session_state['despike_preview_toggle'] = False
                    st.session_state['baseline_preview_toggle'] = False
                    st.rerun()

        else:
            st.session_state['selected_preset'] = None

    else:
        st.caption("No materials configured yet.")
        st.caption("Add one on the **Material Presets** page (top of sidebar).")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Export, View Options, and Reset (moved from the former right-hand
    # control panel in v2.10.0 so the whole workflow lives in the sidebar)
    # ------------------------------------------------------------------
    export_spectrum = get_current_spectrum()

    if export_spectrum is None:
        st.caption("Load a file below to get started.")
    elif not export_spectrum.fit_done:
        st.caption("Run Auto-Workflow to enable export.")
    else:
        st.subheader("Quick Export")

        try:
            export_fig = plot_composite(
                x=export_spectrum.processed_data.X,
                y_data=export_spectrum.processed_data.Y,
                fit_result=export_spectrum.fit_result,
                mode=export_spectrum.mode,
                title=f"{export_spectrum.filename} - Fit Results",
                show_components=True,
            )
        except Exception as e:
            st.error(f"Failed to prepare export: {e}")
            export_fig = None

        if export_fig is not None:
            exp_col1, exp_col2, exp_col3 = st.columns(3)

            with exp_col1:
                st.caption("📷 Static Image")
                try:
                    png_bytes = export_figure_png(export_fig, width=1200, height=600, scale=2.0)
                    filename_png = create_filename(export_spectrum.filename, "fit", "png")
                    st.download_button(
                        label="Download PNG",
                        data=png_bytes,
                        file_name=filename_png,
                        mime="image/png",
                        use_container_width=True
                    )
                except RuntimeError:
                    st.error("PNG export requires kaleido")
                    st.caption("Install: `pip install kaleido`")

            with exp_col2:
                st.caption("🌐 Interactive Plot")
                try:
                    html_string = export_figure_html(export_fig)
                    filename_html = create_filename(export_spectrum.filename, "fit", "html")
                    st.download_button(
                        label="Download HTML",
                        data=html_string,
                        file_name=filename_html,
                        mime="text/html",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"HTML export failed: {e}")

            with exp_col3:
                st.caption("📊 Fit Parameters")
                csv_quick = export_fit_params_csv(export_spectrum)
                filename_csv_quick = create_filename(export_spectrum.filename, "fit_params", "csv")

                st.download_button(
                    label="Download CSV",
                    data=csv_quick,
                    file_name=filename_csv_quick,
                    mime="text/csv",
                    use_container_width=True
                )

        st.markdown("---")

        export_files = st.session_state.get('files', {})
        fitted_files = [f for f in export_files.values() if f.fit_done and f.fit_result and f.fit_result.success]

        if len(fitted_files) > 1:
            st.subheader("Batch Export")
            st.caption(f"Export data from all {len(fitted_files)} fitted files")

            try:
                master_csv = export_master_csv(export_files)

                batch_col1, batch_col2 = st.columns([2, 1])

                with batch_col1:
                    # Default the Save-As dialog to the current file's source
                    # folder, falling back to the last-browsed folder, then the OS default.
                    default_dir = getattr(export_spectrum, 'source_dir', None) \
                        or st.session_state.get('last_picked_dir', '')
                    default_name = create_filename("nexanalyzer", "master_results", "csv")

                    save_clicked = st.button(
                        "💾 Save Master CSV to folder",
                        help="Open a Save-As dialog (pre-pointed at your raw-data folder) "
                             "and type a filename",
                        use_container_width=True
                    )

                with batch_col2:
                    st.metric("Files", len(fitted_files))

                if save_clicked:
                    try:
                        save_path = prompt_save_path(
                            default_dir=default_dir,
                            default_filename=default_name,
                            title="Save Master CSV"
                        )
                        if save_path:
                            with open(save_path, "w", newline="", encoding="utf-8") as f:
                                f.write(master_csv)
                            st.success(f"✅ Saved to {save_path}")
                        # save_path is None => user cancelled => no-op
                    except Exception as e:
                        st.error(f"❌ Failed to save master CSV: {e}")

                st.caption("**Master CSV includes:** Filename, Mode, Peak_Label, Center, Amplitude, FWHM, Shape, R², χ², and standard errors")

            except Exception as e:
                st.error(f"Failed to generate master CSV: {e}")

        elif len(fitted_files) == 1:
            st.caption("Run Auto-Workflow on multiple files to enable batch export")

    st.markdown("---")

    # Reset to Raw
    if export_spectrum is not None:
        if st.button("🔄 Reset to Raw", help="Clear all processing and start over"):
            export_spectrum.reset_to_raw()
            st.success("✅ Reset to raw data")
            st.rerun()

    st.markdown("---")

    # Load spectra
    st.subheader("Load Spectra")

    # Remember the directory of the last picked file for the next dialog's initialdir
    if 'last_picked_dir' not in st.session_state:
        st.session_state['last_picked_dir'] = ""

    # Browse spectrum files button (multi-select)
    if st.button("Browse Spectrum Files", use_container_width=True):
        try:
            import subprocess
            import sys
            import os
            import tempfile
            import json

            # NOTE: askopenfilenames returns a Tcl tuple of paths. Bare print()
            # would mangle paths containing spaces/commas/unicode, so we serialize
            # via json.dumps and parse with json.loads on this side.
            dialog_script = """
import tkinter as tk
from tkinter import filedialog
import sys
import json

root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

initial_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
selected_files = filedialog.askopenfilenames(
    title="Select Spectrum Files",
    initialdir=initial_dir,
    filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
)

root.destroy()
print(json.dumps(list(selected_files)))
"""

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write(dialog_script)
                script_path = f.name

            initial_dir = st.session_state.get('last_picked_dir', '')
            result = subprocess.run(
                [sys.executable, script_path, initial_dir],
                capture_output=True,
                text=True,
                timeout=120
            )

            os.unlink(script_path)

            raw = result.stdout.strip()
            picked = json.loads(raw) if raw else []

            if picked:
                st.session_state['pending_files_to_load'] = picked
                st.session_state['last_picked_dir'] = os.path.dirname(picked[0])
                st.rerun()
            # cancel / empty selection -> no-op, no rerun

        except Exception as e:
            st.error(f"❌ Failed to open file browser: {e}")

    # Process the pending-files queue populated by the Browse button on the previous rerun
    files_to_load = st.session_state.pop('pending_files_to_load', None)
    if files_to_load:
        import os

        loaded_count = 0
        skipped_count = 0

        for file_path in files_to_load:
            filename = os.path.basename(file_path)
            source_dir = os.path.dirname(file_path)  # v2.7: remember source folder for exports

            try:
                # Parse spectrum (returns list; len > 1 for multi-Y files)
                spectra = parse_spectrum_multi(file_path)

                # v2.1+ (FR-12): Auto-detect mode from filename
                detected_mode = detect_mode_from_filename(filename)

                if detected_mode is not None:
                    file_mode = detected_mode
                    auto_detected = True
                    set_mode(detected_mode)
                else:
                    file_mode = "Raman"
                    auto_detected = False

                # Build per-spectrum entries. For multi-Y files, suffix the
                # filename with __1, __2, … so each Y column appears as a
                # separate file entry in the sidebar list.
                base, ext = os.path.splitext(filename)
                n = len(spectra)
                for i, spectrum_data in enumerate(spectra, start=1):
                    entry_name = filename if n == 1 else f"{base}__{i}{ext}"

                    if entry_name in st.session_state.get("files", {}):
                        skipped_count += 1
                        continue

                    spectrum_file = SpectrumFile(
                        filename=entry_name,
                        mode=file_mode,
                        original_data=spectrum_data,
                        raw_data=spectrum_data,
                        processed_data=spectrum_data,
                        source_dir=source_dir,  # v2.7: folder the .txt came from
                        processing_settings=ProcessingSettings(),
                        auto_detected=auto_detected
                    )
                    add_spectrum_file(spectrum_file)
                    loaded_count += 1

            except Exception as e:
                st.error(f"❌ Failed to load {filename}: {e}")

        # Show summary message
        if loaded_count > 0:
            st.success(f"✅ Loaded {loaded_count} file(s)")
            if skipped_count > 0:
                st.info(f"ℹ️ Skipped {skipped_count} already-loaded file(s)")
            st.rerun()
        elif skipped_count > 0:
            st.info(f"ℹ️ All {skipped_count} file(s) already loaded")

    st.markdown("---")

    # File selector
    files = st.session_state.get("files", {})
    if files:
        st.subheader("Loaded Files")

        filenames = list(files.keys())
        current_file = st.session_state.get("current_file")

        # Default to first file if none selected
        if current_file is None or current_file not in filenames:
            st.session_state["current_file"] = filenames[0]
            current_file = filenames[0]

        # File info (selection handled by navigation bar in plot area)
        spectrum = files[current_file]
        st.caption(f"**Mode**: {spectrum.mode}")
        st.caption(f"**Points**: {len(spectrum.raw_data.X)}")
        st.caption(
            f"**Range**: {spectrum.raw_data.X.min():.2f} - {spectrum.raw_data.X.max():.2f}"
        )

        # Remove-file / delete-all buttons (side by side)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Remove File", key=f"remove_{current_file}"):
                remove_spectrum_file(current_file)
                st.rerun()
        with col_b:
            if st.button("🗑️ Delete All", key="delete_all_files",
                         help="Remove all loaded files"):
                clear_all_files()
                st.rerun()

    else:
        st.info("Upload .txt files to begin")

    st.markdown("---")

    # View Options (last item in the sidebar)
    with st.expander("🔍 View Options", expanded=False):
        st.markdown("**Plot Layer Visibility**")

        # No value= here: defaults come from initialize_session_state(), and
        # sync_pending_file_switch() (run before the sidebar) may also have
        # just written these — passing value= as well would make Streamlit
        # warn that the widget's state was set through both paths.
        st.checkbox("Show Raw", key="show_raw",
                   help="Show raw data (before any processing)")

        st.checkbox("Show De-spiked", key="show_despiked",
                   help="Show data after spike removal")

        st.checkbox("Show Baseline-corrected", key="show_corrected",
                   help="Show data after baseline correction")

        st.markdown("---")
        st.markdown("**Peak Fitting Display**")

        st.checkbox("Show Fit", key="show_fit",
                   help="Show total fitted curve")

        st.checkbox("Show Components", key="show_components",
                   help="Show individual peak components")

        st.checkbox("Show Residuals", key="show_residuals",
                   help="Show fit residuals (Baseline-corrected minus Fit Total)")

        st.caption("Toggle plot layers on/off without reprocessing.")
