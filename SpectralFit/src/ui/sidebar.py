"""
Sidebar UI component for mode selection, file upload, and project I/O.

This module provides the render_sidebar() function that displays:
- Mode toggle (Raman / PL)
- File upload widget
- File selector dropdown
- Project save/load buttons
"""

import streamlit as st
from ..models.spectrum import SpectrumFile, ProcessingSettings
from ..processing.parser import parse_spectrum, detect_mode_from_filename
from .session_state import (
    initialize_session_state,
    add_spectrum_file,
    remove_spectrum_file,
    get_mode,
    set_mode
)


def render_sidebar():
    """
    Render sidebar with mode toggle, file upload, and project I/O.

    This function should be called from app.py within a `with st.sidebar:` block.

    Notes
    -----
    - Mode toggle affects axis labels and fitting bounds
    - File upload supports multiple files (batch loading)
    - File selector dropdown shows all loaded files
    - Project save/load will be implemented in Phase 7 (T063-T066)
    """
    # Initialize session state
    initialize_session_state()

    # Mode toggle
    st.header("Settings")
    mode = st.radio(
        "Mode",
        ["Raman", "PL"],
        index=0 if get_mode() == "Raman" else 1,
        help="Raman: cm⁻¹ units, ±5 cm⁻¹ fit bounds\nPL: nm units, ±30 nm fit bounds"
    )
    set_mode(mode)

    st.markdown("---")

    # v2.1+ (FR-14): Plot Width Control
    st.subheader("Display Settings")
    plot_width = st.selectbox(
        "Plot Width",
        options=["Compact", "Standard", "Wide", "Full"],
        index=1,  # Default to "Standard"
        help=(
            "Compact: 60% | Standard: 75% | Wide: 90% | Full: 100%\n\n"
            "Applies to all plots across all tabs."
        ),
        key="plot_width_preset"  # Automatically saves to session_state
    )

    st.markdown("---")

    # v2.3: Material Presets
    st.subheader("Material Presets")

    # Initialize preset-related session state (redundant with session_state.py but kept for safety)
    if 'preset_library' not in st.session_state:
        st.session_state['preset_library'] = None
    if 'selected_preset' not in st.session_state:
        st.session_state['selected_preset'] = None

    # Preset file path input
    preset_path = st.text_input(
        "Preset File Path",
        value=st.session_state.get('preset_file_path', ''),
        placeholder="Path to material_presets.xlsx",
        help="Path to Excel file containing material presets"
    )
    st.session_state['preset_file_path'] = preset_path

    # Reload presets button
    col1, col2 = st.columns([3, 1])
    with col1:
        reload_clicked = st.button("🔄 Reload Presets", use_container_width=True)
    with col2:
        clear_clicked = st.button("✖️", use_container_width=True, help="Clear preset selection")

    if reload_clicked and preset_path:
        try:
            from ..io.preset_parser import parse_preset_excel
            from pathlib import Path

            # Check if file exists
            if not Path(preset_path).exists():
                st.error(f"❌ Preset file not found: {preset_path}")
            else:
                # Parse Excel file
                with st.spinner("Loading presets..."):
                    preset_library = parse_preset_excel(preset_path)
                    st.session_state['preset_library'] = preset_library
                    st.session_state['selected_preset'] = None  # Reset selection

                st.success(f"✅ Loaded {preset_library.get_sheet_count()} preset(s)")

        except Exception as e:
            st.error(f"❌ Failed to load presets: {e}")

    if clear_clicked:
        st.session_state['selected_preset'] = None
        st.rerun()

    # Material selector (only show if presets are loaded and files exist)
    preset_library = st.session_state.get('preset_library')
    files = st.session_state.get("files", {})
    current_file = st.session_state.get("current_file")

    if preset_library and files and current_file:
        current_spectrum = files[current_file]
        current_mode = current_spectrum.mode

        # Get materials for current mode
        available_materials = preset_library.list_materials(mode=current_mode)

        if available_materials:
            # Material dropdown
            selected_material = st.selectbox(
                "Select Material",
                options=["(None)"] + available_materials,
                index=0,
                help=f"Materials for {current_mode} mode"
            )

            if selected_material != "(None)":
                # Get preset (selected_material is now full sheet name like "WSe2_Raman")
                preset = preset_library.get_preset(selected_material)
                st.session_state['selected_preset'] = preset

                # Display preset info
                st.caption(f"**Baseline**: {preset.baseline_algorithm}")
                st.caption(f"**Peaks**: {len(preset.peak_templates)}")
                if preset.description:
                    st.caption(f"**Notes**: {preset.description}")

                # Run Auto-Workflow button
                if st.button("🚀 Run Auto-Workflow", type="primary", use_container_width=True):
                    # Execute auto-workflow immediately (single-click behavior)
                    from ..processing.auto_workflow import execute_auto_workflow, format_workflow_summary, get_workflow_suggestions

                    with st.spinner("🚀 Executing automated workflow..."):
                        result = execute_auto_workflow(current_spectrum, preset)

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

                        for idx, (filename, spectrum) in enumerate(file_items):
                            status_text.text(f"Processing {idx + 1}/{total}: {filename}")
                            progress_bar.progress((idx + 1) / total)

                            result = execute_auto_workflow(spectrum, preset)
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
            st.info(f"ℹ️ No {current_mode} presets found. Add a '{current_mode}' sheet to Excel file.")

    elif preset_library and not files:
        st.caption("Load spectrum files to use presets")
    elif not preset_library:
        st.caption("Click 'Reload' to load presets")

    st.markdown("---")

    # Folder browser
    st.subheader("Load Spectra")

    # Initialize last folder path in session state if not exists
    if 'last_folder_path' not in st.session_state:
        st.session_state['last_folder_path'] = ""

    # Text input for folder path
    folder_path = st.text_input(
        "Folder Path",
        value=st.session_state.get('last_folder_path', ''),
        placeholder="Enter or paste folder path here",
        help="Enter the full path to a folder containing .txt spectrum files"
    )

    # Browse folder button
    if st.button("Browse File Folder", use_container_width=True):
        try:
            import subprocess
            import sys
            import os

            # Create a separate Python script to run tkinter dialog
            dialog_script = """
import tkinter as tk
from tkinter import filedialog
import sys

root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

initial_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
selected_folder = filedialog.askdirectory(
    title="Select Folder Containing Spectrum Files",
    initialdir=initial_dir
)

root.destroy()
print(selected_folder)
"""

            # Write script to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write(dialog_script)
                script_path = f.name

            # Run dialog in separate process
            initial_dir = st.session_state.get('last_folder_path', '')
            result = subprocess.run(
                [sys.executable, script_path, initial_dir],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Clean up temp file
            os.unlink(script_path)

            # Get selected folder from output
            selected_folder = result.stdout.strip()

            if selected_folder:
                # Update folder path in session state and text input
                st.session_state['last_folder_path'] = selected_folder
                st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to open folder browser: {e}")

    # Load files from folder when path is provided
    if folder_path and folder_path != st.session_state.get('loaded_folder_path', ''):
        try:
            import os
            import glob

            # Store the loaded folder path to prevent reloading
            st.session_state['loaded_folder_path'] = folder_path

            # Find all .txt files in the folder
            txt_files = glob.glob(os.path.join(folder_path, "*.txt"))

            if not txt_files:
                st.warning(f"⚠️ No .txt files found in: {folder_path}")
            else:
                # Load each .txt file
                loaded_count = 0
                skipped_count = 0

                for file_path in txt_files:
                    filename = os.path.basename(file_path)

                    # Check if already loaded
                    if filename in st.session_state.get("files", {}):
                        skipped_count += 1
                        continue

                    try:
                        # Parse spectrum
                        spectrum_data = parse_spectrum(file_path)

                        # v2.1+ (FR-12): Auto-detect mode from filename
                        detected_mode = detect_mode_from_filename(filename)

                        if detected_mode is not None:
                            # Use detected mode and mark as auto-detected
                            file_mode = detected_mode
                            auto_detected = True
                            set_mode(detected_mode)  # Update global mode
                        else:
                            # Use current mode setting
                            file_mode = mode
                            auto_detected = False

                        # Create SpectrumFile
                        spectrum_file = SpectrumFile(
                            filename=filename,
                            mode=file_mode,
                            original_data=spectrum_data,
                            raw_data=spectrum_data,
                            processed_data=spectrum_data,
                            processing_settings=ProcessingSettings(),
                            auto_detected=auto_detected
                        )

                        # Add to session state
                        add_spectrum_file(spectrum_file)
                        loaded_count += 1

                    except Exception as e:
                        st.error(f"❌ Failed to load {filename}: {e}")

                # Show summary message
                if loaded_count > 0:
                    st.success(f"✅ Loaded {loaded_count} file(s) from folder")
                    if skipped_count > 0:
                        st.info(f"ℹ️ Skipped {skipped_count} already loaded file(s)")
                    st.rerun()
                elif skipped_count > 0:
                    st.info(f"ℹ️ All {skipped_count} file(s) already loaded")

        except Exception as e:
            st.error(f"❌ Failed to load files from folder: {e}")
            st.session_state['loaded_folder_path'] = ""  # Reset on error

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

        # Remove file button
        if st.button("Remove File", key=f"remove_{current_file}"):
            remove_spectrum_file(current_file)
            st.rerun()

    else:
        st.info("Upload .txt files to begin")

    st.markdown("---")

    # Project I/O
    st.subheader("Project")

    # Save project
    if files:
        if st.button("Save Project"):
            try:
                from ..io.project_io import save_project
                import tempfile
                import os

                # Create temp file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                    tmp_path = tmp_file.name

                # Save project
                save_project(files, tmp_path, include_arrays=True)

                # Read file content
                with open(tmp_path, 'r') as f:
                    json_content = f.read()

                # Clean up temp file
                os.unlink(tmp_path)

                # Offer download
                st.download_button(
                    "📥 Download Project JSON",
                    data=json_content,
                    file_name="spectralfit_project.json",
                    mime="application/json",
                    help="Save all loaded files and their processing state"
                )

            except Exception as e:
                st.error(f"❌ Save failed: {e}")
    else:
        st.caption("Load files before saving project")

    # Load project
    uploaded_project = st.file_uploader(
        "Load Project",
        type=["json"],
        accept_multiple_files=False,
        help="Load previously saved SpectralFit project"
    )

    if uploaded_project:
        try:
            from ..io.project_io import load_project
            import tempfile
            import os

            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.json') as tmp_file:
                tmp_file.write(uploaded_project.read())
                tmp_path = tmp_file.name

            # Load project
            loaded_files = load_project(tmp_path)

            # Update session state
            st.session_state["files"] = loaded_files

            # Set first file as current
            if loaded_files:
                st.session_state["current_file"] = list(loaded_files.keys())[0]

            # Clean up temp file
            os.unlink(tmp_path)

            st.success(f"✅ Loaded project with {len(loaded_files)} file(s)")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Load failed: {e}")
