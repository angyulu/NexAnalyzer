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

    # File upload
    st.subheader("Load Spectra")
    uploaded_files = st.file_uploader(
        "Upload .txt files",
        type=["txt"],
        accept_multiple_files=True,
        help="Two-column format: X<tab|comma>Y\nNo header row, numeric values only"
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Check if already loaded
            if uploaded_file.name in st.session_state.get("files", {}):
                continue

            try:
                # Save to temp file and parse
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name

                # Parse spectrum
                spectrum_data = parse_spectrum(tmp_path)

                # v2.1+ (FR-12): Auto-detect mode from filename
                detected_mode = detect_mode_from_filename(uploaded_file.name)

                if detected_mode is not None:
                    # Use detected mode and mark as auto-detected
                    file_mode = detected_mode
                    auto_detected = True
                    set_mode(detected_mode)  # Update global mode

                    # Display info banner
                    st.info(
                        f"ℹ️ Mode auto-detected as **{detected_mode}** from filename; "
                        "change manually if incorrect."
                    )
                else:
                    # Use current mode setting
                    file_mode = mode
                    auto_detected = False

                # Create SpectrumFile
                spectrum_file = SpectrumFile(
                    filename=uploaded_file.name,
                    mode=file_mode,
                    raw_data=spectrum_data,
                    processed_data=spectrum_data,  # Initially same as raw
                    processing_settings=ProcessingSettings(),
                    auto_detected=auto_detected
                )

                # Add to session state
                add_spectrum_file(spectrum_file)

                # Clean up temp file
                os.unlink(tmp_path)

                st.success(f"✅ Loaded: {uploaded_file.name}")

            except Exception as e:
                st.error(f"❌ Failed to load {uploaded_file.name}: {e}")

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

        # Dropdown selector
        selected = st.selectbox(
            "Select file",
            filenames,
            index=filenames.index(current_file) if current_file in filenames else 0,
            help="Select a spectrum file to process"
        )

        st.session_state["current_file"] = selected

        # File info
        spectrum = files[selected]
        st.caption(f"**Mode**: {spectrum.mode}")
        st.caption(f"**Points**: {len(spectrum.raw_data.X)}")
        st.caption(
            f"**Range**: {spectrum.raw_data.X.min():.2f} - {spectrum.raw_data.X.max():.2f}"
        )

        # Remove file button
        if st.button("Remove File", key=f"remove_{selected}"):
            remove_spectrum_file(selected)
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
