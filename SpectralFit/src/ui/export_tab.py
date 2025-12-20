"""
Export tab UI component.

This tab provides:
- Composite plot visualization (data + fit + components + residuals)
- Styling controls panel
- Export options (PNG, HTML, CSV)
"""

import streamlit as st
from .session_state import get_current_spectrum, get_styling, update_styling
from ..models.project import StylingPreferences


def render_export_tab():
    """
    Render export tab (visualization and export options).

    This function should be called from app.py within a tab context.
    """
    spectrum = get_current_spectrum()

    if spectrum is None:
        st.info("📁 Upload a spectrum file to begin visualization")
        return

    st.header(f"Visualize & Export: {spectrum.filename}")

    # Plot visualization
    st.subheader("Composite Plot")
    st.caption("Layout: 3/4 main plot (data + fit + components) + 1/4 residuals subplot")

    if spectrum.fit_result is None or not spectrum.fit_result.success:
        st.warning("⚠️ No fit results yet. Complete fitting in the 'Fit Peaks' tab first.")
    else:
        try:
            from ..visualization.plotter import plot_composite

            # Get current styling
            styling = get_styling()

            # Create plot with current styling
            fig = plot_composite(
                spectrum.processed_data.X,
                spectrum.processed_data.Y,
                spectrum.fit_result,
                mode=spectrum.mode,
                title=f"Fit Results: {spectrum.filename}",
                show_components=st.checkbox("Show Individual Components", value=True)
            )

            # Apply styling preferences (basic customization)
            # Note: Full styling integration would require updating plot_composite
            # This is a simplified version for Phase 5

            st.plotly_chart(fig, use_container_width=True, key="export_plot")

        except Exception as e:
            st.error(f"❌ Plot failed: {e}")

    st.markdown("---")

    # Styling panel
    with st.expander("Styling Options", expanded=False):
        st.subheader("Plot Styling")
        st.caption("Customize plot appearance (changes will apply on next plot refresh)")

        styling = get_styling()

        # Data styling
        st.markdown("**Data Points**")
        col1, col2 = st.columns(2)
        with col1:
            data_color = st.color_picker("Data Color", value=styling.data_color)
        with col2:
            data_line_width = st.slider("Line Width", 0.5, 5.0, styling.data_line_width, step=0.5)

        data_marker_style = st.radio(
            "Marker Style",
            ["markers", "lines", "markers+lines"],
            index=["markers", "lines", "markers+lines"].index(styling.data_marker_style)
        )

        # Fit styling
        st.markdown("**Fit Curve**")
        col3, col4 = st.columns(2)
        with col3:
            fit_color = st.color_picker("Fit Color", value=styling.fit_color)
        with col4:
            fit_line_width = st.slider("Fit Line Width", 0.5, 5.0, styling.fit_line_width, step=0.5)

        fit_line_style = st.radio(
            "Fit Line Style",
            ["solid", "dash", "dot"],
            index=["solid", "dash", "dot"].index(styling.fit_line_style)
        )

        # Residual styling
        st.markdown("**Residuals**")
        residual_color = st.color_picker("Residual Color", value=styling.residual_color)

        # Apply button
        if st.button("Apply Styling"):
            new_styling = StylingPreferences(
                data_color=data_color,
                data_line_width=data_line_width,
                data_marker_style=data_marker_style,
                fit_color=fit_color,
                fit_line_width=fit_line_width,
                fit_line_style=fit_line_style,
                residual_color=residual_color,
                peak_colors=styling.peak_colors  # Preserve existing peak colors
            )
            update_styling(new_styling)
            st.success("✅ Styling updated")
            st.rerun()

    st.markdown("---")

    # Export section
    st.subheader("Export")

    if spectrum.fit_result is None or not spectrum.fit_result.success:
        st.caption("Export will be available after successful fitting")
    else:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**PNG Image**")
            st.caption("Static high-resolution image")

            if st.button("Download PNG"):
                try:
                    from ..visualization.plotter import plot_composite
                    from ..io.export import export_figure_png, create_filename

                    fig = plot_composite(
                        spectrum.processed_data.X,
                        spectrum.processed_data.Y,
                        spectrum.fit_result,
                        mode=spectrum.mode,
                        title=f"Fit Results: {spectrum.filename}",
                        show_components=True
                    )

                    png_bytes = export_figure_png(fig, width=1200, height=800, scale=2.0)
                    filename = create_filename(spectrum.filename, "fit", "png")

                    st.download_button(
                        "📥 Download PNG",
                        data=png_bytes,
                        file_name=filename,
                        mime="image/png"
                    )

                except Exception as e:
                    st.error(f"❌ PNG export failed: {e}")
                    st.caption("Note: PNG export requires 'kaleido' package. Install with: pip install kaleido")

        with col2:
            st.markdown("**HTML Interactive**")
            st.caption("Fully interactive plot")

            if st.button("Download HTML"):
                try:
                    from ..visualization.plotter import plot_composite
                    from ..io.export import export_figure_html, create_filename

                    fig = plot_composite(
                        spectrum.processed_data.X,
                        spectrum.processed_data.Y,
                        spectrum.fit_result,
                        mode=spectrum.mode,
                        title=f"Fit Results: {spectrum.filename}",
                        show_components=True
                    )

                    html_string = export_figure_html(fig)
                    filename = create_filename(spectrum.filename, "fit", "html")

                    st.download_button(
                        "📥 Download HTML",
                        data=html_string,
                        file_name=filename,
                        mime="text/html"
                    )

                except Exception as e:
                    st.error(f"❌ HTML export failed: {e}")

        with col3:
            st.markdown("**CSV Data**")
            st.caption("Fit results table")

            if st.button("Download CSV"):
                try:
                    from ..io.export import export_master_csv, create_filename

                    # Export current file only
                    files = {spectrum.filename: spectrum}
                    csv_string = export_master_csv(files)
                    filename = create_filename(spectrum.filename, "results", "csv")

                    st.download_button(
                        "📥 Download CSV",
                        data=csv_string,
                        file_name=filename,
                        mime="text/csv"
                    )

                except Exception as e:
                    st.error(f"❌ CSV export failed: {e}")

    # Batch export (if multiple files)
    if st.session_state.get("files") and len(st.session_state["files"]) > 1:
        st.markdown("---")
        st.subheader("Batch Export")
        st.caption(f"Export all {len(st.session_state['files'])} loaded files")

        if st.button("Download Master CSV (All Files)"):
            try:
                from ..io.export import export_master_csv

                csv_string = export_master_csv(st.session_state["files"])

                st.download_button(
                    "📥 Download Master CSV",
                    data=csv_string,
                    file_name="spectralfit_master_results.csv",
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"❌ Batch export failed: {e}")
