"""
Sample Report page: pick a sample folder containing a 9-point Raman/PL/OM
measurement grid, fit all 18 spectra against one material's presets, and
generate a three-slide PPTX report: an overview slide (3x3 OM grid + fit
summary tables), a 3x3 grid of each Raman point's fitted spectrum, and the
same for PL.
"""

import io
import os
from datetime import date

import streamlit as st
from PIL import Image

from core.io.export import export_figure_png, prompt_save_path
from core.io.folder_picker import prompt_folder_path
from core.report.pptx import FIT_COLUMN_ASPECT_RATIO, FIT_GRID_COLUMNS, build_sample_report_pptx
from modules.spectra.io.preset_store import load_presets
from core.io.report_settings import load_default_material, save_default_material
from core.report.progress import build as build_progress
from core.report.slides import render_slides_to_png
from modules.spectra.processing.peak_metrics import (
    aggregate_fit_results,
    aggregate_raw_peak_stats,
    compute_peak_intensity_ratio,
)
from modules.spectra.processing.sample_batch import run_sample_batch
from modules.spectra.processing.sample_scanner import default_magnification, scan_sample_folder
from modules.spectra.ui.sample_report_state import get_sample_report_state
from modules.spectra.viz.fit_plot import (
    fit_legend_entries,
    peak_normalization_scale,
    plot_fit_column,
    shared_axis_ranges,
    y_axis_title,
)

# WSe2-specific defect/strain indicators: mode intensities relative to the E2g+A1g
# in-plane mode, appended as extra rows of the Raman fit-summary table. Any pair
# whose labels aren't both present in a fit is dropped automatically (see
# compute_peak_intensity_ratio), so this list is safe for other materials. The
# table's caption says which rows are medians; putting it on each label instead
# wrapped the cell, which doubled the row's height and overran the table below.
_RAMAN_RATIO_PAIRS = [("LA", "E2g+A1g"), ("B2g", "E2g+A1g")]

_SLIDE_CAPTIONS = ["Overview — OM + fit summary", "Raman — fitted spectra", "PL — fitted spectra"]

st.title("🖼️ Sample Report")
st.markdown(
    "Generate a three-slide PPTX report from a sample folder's 9-point "
    "Raman + PL + OM measurement grid."
)

state = get_sample_report_state()

# ---------------------------------------------------------------- Folder pick
st.subheader("1. Sample Folder")
col_pick, col_path = st.columns([1, 3])
with col_pick:
    pick_clicked = st.button("Select Sample Folder", use_container_width=True)
with col_path:
    st.caption(state["folder"] or "No folder selected yet.")

if pick_clicked:
    try:
        picked = prompt_folder_path(default_dir=state["folder"] or "")
    except Exception as e:
        st.error(f"Failed to open folder browser: {e}")
        picked = None

    if picked:
        state["folder"] = picked
        state["scan"] = scan_sample_folder(picked)
        state["magnification"] = default_magnification(state["scan"])
        state["batch_result"] = None
        state["raman_stats"] = None
        state["pl_stats"] = None
        state["pptx_bytes"] = None
        state["slide_images"] = None
        st.rerun()

scan = state["scan"]

if scan is not None:
    n_images = sum(len(v) for v in scan.image_files.values())
    st.success(
        f"**{scan.sample_name}** — {len(scan.raman_files)} Raman, "
        f"{len(scan.pl_files)} PL, {n_images} image file(s)"
    )

    if scan.ignored_files:
        with st.expander(f"{len(scan.ignored_files)} file(s) ignored (didn't match naming pattern)"):
            st.write(", ".join(scan.ignored_files))

    # -------------------------------------------------------- Magnification
    st.subheader("2. OM Magnification")
    magnifications = scan.magnifications()
    if magnifications:
        current_mag = state["magnification"] if state["magnification"] in magnifications else magnifications[0]
        state["magnification"] = st.selectbox(
            "Magnification group", options=magnifications, index=magnifications.index(current_mag)
        )
    else:
        st.caption("No OM images found in this folder.")

    # -------------------------------------------------------------- Material
    st.subheader("3. Material")
    presets = load_presets()
    materials = sorted({name for (name, _mode), p in presets.items() if p.enabled})

    if not materials:
        st.warning("No materials configured yet. Add one on the **Material Presets** page.")
    else:
        default_material = load_default_material()
        current_material = state["material"] if state["material"] in materials else (
            default_material if default_material in materials else materials[0]
        )
        material_selection = st.selectbox(
            "Material", options=materials, index=materials.index(current_material)
        )
        if material_selection != state["material"]:
            state["material"] = material_selection
            save_default_material(material_selection)

        raman_preset = presets.get((state["material"], "Raman"))
        pl_preset = presets.get((state["material"], "PL"))
        if raman_preset is None:
            st.caption("No Raman preset for this material — the Raman section will be omitted.")
        if pl_preset is None:
            st.caption("No PL preset for this material — the PL section will be omitted.")

        # ------------------------------------------------------------ Generate
        st.subheader("4. Generate Report")
        has_any_content = bool(scan.raman_files) or bool(scan.pl_files) or bool(scan.image_files)

        generate_clicked = st.button(
            "🚀 Generate Report", type="primary", use_container_width=True,
            disabled=not has_any_content,
        )

        if generate_clicked:
            om_paths = {
                point: path
                for point, path in scan.image_files.get(state["magnification"], {}).items()
                if 1 <= point <= 9
            }

            # One status for the whole build, not just the fitting stage. The
            # `with` form is load-bearing: on the way out it resolves the
            # status to complete, or to error if the body raised. A bare
            # handle would leave it spinning forever on a failure, which is
            # exactly the "did it hang?" the progress is here to answer.
            with st.status("Generating report...", expanded=True) as status:
                progress_bar = st.progress(0.0, text="Starting...")

                def _report(fraction, message):
                    progress_bar.progress(fraction, text=message)
                    status.update(label=message)

                progress = build_progress(
                    _report,
                    has_raman=bool(scan.raman_files),
                    has_pl=bool(scan.pl_files),
                    has_optical=bool(om_paths),
                )

                has_spectra = bool(scan.raman_files) or bool(scan.pl_files)
                if has_spectra:
                    progress.start("fit")
                batch_result = run_sample_batch(
                    scan, raman_preset, pl_preset,
                    max_iterations=st.session_state.get("max_iterations", 2000),
                    progress_callback=progress.sub_callback(
                        "fit",
                        # Both techniques share the one fitting stage, and each
                        # counts from 1 again, so the stage needs their combined
                        # total or the bar stalls through the second one.
                        totals={
                            "Raman": len(scan.raman_files),
                            "PL": len(scan.pl_files),
                        },
                    ) if has_spectra else None,
                )
                if has_spectra:
                    progress.complete("fit")
                state["batch_result"] = batch_result

                # Same traces as the Analysis page's fit results (data + total fit
                # + peak components), minus the residuals strip, which is unreadable
                # at this size and only steals height from the spectrum. Rendered at
                # the pptx layout's column aspect ratio so each image fills its
                # column instead of being letterboxed.
                column_width_px = 1000
                column_height_px = round(column_width_px / FIT_COLUMN_ASPECT_RATIO)

                def _build_fit_columns(point_spectra, mode, stage_key):
                    """One image per grid column, each holding that column's three
                    points on a single shared X-axis: column 0 is points 1/4/7,
                    column 1 is 2/5/8, column 2 is 3/6/9.

                    Reports per column, because each column is one kaleido
                    rasterization costing ~1.3 s and there is no progress to be
                    had inside one. Six of them is most of the wait."""
                    by_point = dict(point_spectra)

                    # Ranges are computed from the normalized series, because that
                    # is what actually gets drawn — every point divided by its own
                    # tallest peak, so each panel's peak lands at 1.0.
                    normalized = []
                    for _point, s in point_spectra:
                        scale = peak_normalization_scale(s.processed_data.Y, s.fit_result)
                        curve = s.fit_result.total_fit_curve if s.fit_result else None
                        normalized.append((
                            s.processed_data.X,
                            s.processed_data.Y / scale,
                            None if curve is None else curve / scale,
                        ))
                    x_range, y_range = shared_axis_ranges(normalized)

                    images = {}
                    progress.start(stage_key, detail=f"0/{FIT_GRID_COLUMNS}")
                    for col in range(FIT_GRID_COLUMNS):
                        column_points = [
                            (
                                point,
                                by_point[point].processed_data.X,
                                by_point[point].processed_data.Y,
                                by_point[point].fit_result,
                            )
                            for point in (col + 1, col + 4, col + 7)
                            if point in by_point
                        ]
                        if not column_points:
                            continue  # placeholder column; nothing to render

                        fig = plot_fit_column(
                            column_points, mode=mode, show_components=True,
                            x_range=x_range, y_range=y_range, normalize=True,
                        )
                        images[col] = export_figure_png(
                            fig, width=column_width_px, height=column_height_px, scale=2.0
                        )
                        progress.tick(stage_key, col + 1, FIT_GRID_COLUMNS)
                    return images

                raman_fit_columns = (
                    _build_fit_columns(batch_result.raman_spectra, "Raman", "raman_figures")
                    if batch_result.raman_spectra else {}
                )
                pl_fit_columns = (
                    _build_fit_columns(batch_result.pl_spectra, "PL", "pl_figures")
                    if batch_result.pl_spectra else {}
                )

                # Keys for those grids. None where the technique produced no fits,
                # so an all-placeholder slide doesn't get a legend for nothing.
                raman_legend = (
                    fit_legend_entries([s.fit_result for _, s in batch_result.raman_spectra])
                    if batch_result.raman_spectra else None
                )
                pl_legend = (
                    fit_legend_entries([s.fit_result for _, s in batch_result.pl_spectra])
                    if batch_result.pl_spectra else None
                )

                state["raman_stats"] = (
                    aggregate_fit_results([s.fit_result for _, s in batch_result.raman_spectra])
                    if batch_result.raman_spectra else None
                )
                # PL leads with the empirical measurement — the tallest point of each
                # processed spectrum, no fit involved — then the fitted peaks. Same
                # "Raw" row the on-screen table and the master CSV already show.
                if batch_result.pl_spectra:
                    pl_spectra = [s for _, s in batch_result.pl_spectra]
                    pl_stats = aggregate_fit_results([s.fit_result for s in pl_spectra])
                    raw_stat = aggregate_raw_peak_stats(pl_spectra)
                    state["pl_stats"] = ([raw_stat] + pl_stats) if raw_stat else pl_stats
                else:
                    state["pl_stats"] = None
                raman_fits = [s.fit_result for _, s in batch_result.raman_spectra]
                raman_ratios = []
                for numerator, denominator in _RAMAN_RATIO_PAIRS:
                    ratio = compute_peak_intensity_ratio(raman_fits, numerator, denominator)
                    if ratio is not None:
                        raman_ratios.append((f"{numerator} / {denominator}", ratio))

                # Per image, not per batch: these are ~0.6 s each for a real
                # 2240x1680 microscope frame, and if the folder lives on OneDrive
                # a cloud-only file has to be downloaded first, which no estimate
                # can predict. Ticking keeps the bar moving through it either way.
                om_png_bytes = {}
                if om_paths:
                    progress.start("optical_images", detail=f"0/{len(om_paths)}")
                    for done, (point, path) in enumerate(sorted(om_paths.items()), start=1):
                        try:
                            with Image.open(path) as im:
                                buf = io.BytesIO()
                                im.convert("RGB").save(buf, format="PNG")
                            om_png_bytes[point] = buf.getvalue()
                        except Exception as e:
                            st.warning(f"Could not load image for point {point}: {e}")
                        progress.tick("optical_images", done, len(om_paths))

                # No inner progress to report: python-pptx assembly is one opaque
                # call (~2 s, and it re-encodes every embedded image). The status
                # spinner carries liveness while the bar holds still.
                progress.start("pptx")
                state["pptx_bytes"] = build_sample_report_pptx(
                    sample_name=scan.sample_name,
                    material_name=state["material"],
                    report_date=date.today().isoformat(),
                    magnification_label=state["magnification"],
                    om_image_bytes=om_png_bytes,
                    raman_stats=state["raman_stats"],
                    raman_fit_columns=raman_fit_columns,
                    pl_stats=state["pl_stats"],
                    pl_fit_columns=pl_fit_columns,
                    raman_ratios=raman_ratios,
                    raman_fit_legend=raman_legend,
                    pl_fit_legend=pl_legend,
                    fit_y_label=y_axis_title(normalized=True),
                )

                progress.complete("pptx")

                # The longest opaque block: this spawns PowerPoint over COM to
                # rasterize the slides. Named explicitly, because a user who knows
                # PowerPoint is starting reads a still bar as work, not a crash.
                progress.start("preview", detail="launching PowerPoint")
                try:
                    state["slide_images"] = render_slides_to_png(state["pptx_bytes"])
                except RuntimeError as e:
                    state["slide_images"] = None
                    st.warning(f"Report saved, but couldn't render a preview ({e}).")
                progress.complete("preview")

                progress.finish()
                status.update(
                    label=f"Report generated for {scan.sample_name}.",
                    state="complete",
                    expanded=False,
                )

            # Outside the status: it collapses itself once complete, and a
            # collapsed container is no place for the list of points that
            # failed to fit.
            errors = batch_result.raman_errors + batch_result.pl_errors
            if errors:
                with st.expander(f"{len(errors)} point(s) failed to fit and were excluded"):
                    for point, err in errors:
                        st.error(f"Point {point}: {err}")

            st.success("Report generated.")

        # ------------------------------------------------------------- Preview
        if state["slide_images"]:
            st.subheader("Preview")
            for png_bytes, caption in zip(state["slide_images"], _SLIDE_CAPTIONS):
                st.image(png_bytes, caption=caption, use_container_width=True)

        # ---------------------------------------------------------------- Save
        if state["pptx_bytes"] is not None:
            st.subheader("5. Save Report")
            if st.button("💾 Save Report As...", use_container_width=True):
                try:
                    save_path = prompt_save_path(
                        default_dir=state["folder"],
                        default_filename=f"{scan.sample_name}_Report.pptx",
                        title="Save Sample Report",
                        filetypes=(("PowerPoint files", "*.pptx"), ("All files", "*.*")),
                        default_extension=".pptx",
                    )
                    if save_path:
                        with open(save_path, "wb") as f:
                            f.write(state["pptx_bytes"])

                        saved_files = [save_path]
                        if state["slide_images"]:
                            base, _ext = os.path.splitext(save_path)
                            for i, png_bytes in enumerate(state["slide_images"], start=1):
                                image_path = f"{base}_page{i}.png"
                                with open(image_path, "wb") as f:
                                    f.write(png_bytes)
                                saved_files.append(image_path)

                        st.success("Saved:\n" + "\n".join(f"- {p}" for p in saved_files))
                    # save_path is None => user cancelled => no-op
                except Exception as e:
                    st.error(f"Failed to save report: {e}")
