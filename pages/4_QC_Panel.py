"""
QC Panel: the analysis figures for one sample, on screen.

Two images, produced from the same sample folder the Sample Report reads:

  Image 1  OM  — layer segmentation across the grid positions, plus the
                 histogram diagnostics that show where each threshold landed.
  Image 2  Raman — fitted FWHM, peak centres and diagnostic ratios across the
                 same positions, with the inherited spec lines drawn.

A technique with no data is skipped rather than drawn empty, so an OM+Raman
sample like TSM260803 produces two images and no PL placeholder.

The OM image is produced twice: a clean copy for a report, and a diagnostic
copy carrying the green-channel histograms. The histograms are what make a
saturated frame legible *as* one, which an internal reviewer needs and a
customer reading a report does not.

Run-and-view by design: press Run, look at the result. The segmentation's
tunables — `nsigma`, `minpx`, the mask margin and the flat-field divisor — come
from the material preset's optical block for the chosen layer, so a figure's
numbers are still reproducible from the sample folder plus the committed
preset. Tune them on the Material Presets page, not per run;
docs/OM_Contrast_Algo.md says when each is worth moving. A layer with no block
of its own runs the algorithm's own defaults, and the page says so.
"""

import os

import streamlit as st

from core.io.export import prompt_save_path
from core.io.folder_picker import prompt_folder_path
from core.io.report_settings import load_default_material, save_default_material
from modules.optical.processing.contrast import (
    REFERENCE_CHOICES,
    analyse_frame,
    class_summary,
    layer_word,
)
from modules.optical.ui.qc_panel_state import (
    get_qc_panel_state,
    reset_optical_results,
    reset_raman_results,
    reset_results,
)
from modules.optical.viz.om_grid import build_om_grid_figure
from modules.spectra.io.preset_store import load_presets
from modules.spectra.processing.peak_metrics import (
    R_SQUARED_MIN,
    aggregate_fit_results,
    filter_fits_by_quality,
)
from modules.spectra.processing.sample_batch import run_sample_batch
from modules.spectra.processing.sample_scanner import default_magnification, scan_sample_folder
from modules.spectra.utils.preset_staleness import optical_fingerprint, technique_fingerprint
from modules.spectra.viz.raman_quality import build_raman_quality_figure

st.title("🔬 QC Panel")
st.markdown(
    "Layer segmentation and Raman quality figures for one sample folder. "
    "Images without data are skipped."
)

state = get_qc_panel_state()

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
        reset_results(state)
        st.rerun()

scan = state["scan"]

if scan is not None:
    n_images = sum(len(v) for v in scan.image_files.values())
    st.success(
        f"**{scan.sample_name}** — {len(scan.raman_files)} Raman, "
        f"{len(scan.pl_files)} PL, {n_images} image file(s)"
    )

    # ------------------------------------------------------ Magnification
    st.subheader("2. OM Magnification")
    magnifications = scan.magnifications()
    if magnifications:
        current = state["magnification"] if state["magnification"] in magnifications else magnifications[0]
        state["magnification"] = st.selectbox(
            "Magnification group", options=magnifications, index=magnifications.index(current)
        )
    else:
        st.caption("No OM images found — Image 1 will be skipped.")

    # ------------------------------------------------------------- Layer
    st.subheader("3. Layer")
    reference = st.selectbox(
        "The film being measured",
        options=REFERENCE_CHOICES,
        index=REFERENCE_CHOICES.index(state.get("reference_layer", "2L")),
        # layer_word() is presentation only; "1L"/"2L" is what gets stored and
        # what keys the preset's optical block.
        format_func=lambda r: f"{r} — {layer_word(r).lower()} film",
    )
    if reference != state.get("reference_layer"):
        state["reference_layer"] = reference
        reset_results(state)
    # Worth stating plainly: with identical tuning the segmentation is the same
    # either way, so a wrong choice here relabels every class by one layer with
    # no visible symptom in the figure.
    st.caption(
        f"Classes will be labelled **Below {reference}**, "
        f"**{layer_word(reference)}**, **Above {reference}**. "
        "The algorithm cannot infer this — a wrong choice mislabels every class "
        "by one layer, and selects a different tuning block."
    )

    # ------------------------------------------------------------ Material
    st.subheader("4. Material")
    presets = load_presets()
    materials = sorted(name for name, p in presets.items() if p.enabled)

    if not materials:
        st.warning("No materials configured yet. Add one on the **Material Presets** page.")
    else:
        default_material = load_default_material()
        current_material = state["material"] if state["material"] in materials else (
            default_material if default_material in materials else materials[0]
        )
        selection = st.selectbox("Material", options=materials,
                                 index=materials.index(current_material))
        if selection != state["material"]:
            state["material"] = selection
            save_default_material(selection)
            reset_results(state)

        selected = presets.get(state["material"])
        raman_preset = selected if (selected and selected.block_for("Raman")) else None
        if raman_preset is None:
            st.caption("No Raman settings for this material — Image 2 will be skipped.")

        # Optical tuning for the chosen layer. Never None: an untuned layer
        # runs contrast.py's own defaults, which is a legitimate state and one
        # the operator should be told about rather than blocked by.
        optical = selected.optical_for(reference) if selected else None
        if selected is not None:
            tuned = reference in selected.optical
            settings = optical.as_kwargs()
            if tuned and settings:
                st.caption(
                    f"Optical tuning from **{state['material']} / {reference}**: "
                    + ", ".join(f"`{k}`={v}" for k, v in sorted(settings.items()))
                )
            else:
                st.caption(
                    f"**{state['material']}** has no optical tuning for "
                    f"{layer_word(reference).lower()} films — running the "
                    f"algorithm's own defaults. Add a block on the "
                    f"**Material Presets** page to tune it."
                )

        # Drop only what a preset edit invalidates. Editing a Raman peak must
        # not discard a 30-second OM segmentation, and vice versa.
        _optical_now = optical_fingerprint(selected, reference)
        _raman_now = technique_fingerprint(selected, "Raman")
        if state.get("om_png") and state.get("optical_fingerprint") != _optical_now:
            reset_optical_results(state)
            st.info("The optical settings changed — re-run to rebuild Image 1.")
        if state.get("raman_png") and state.get("raman_fingerprint") != _raman_now:
            reset_raman_results(state)
            st.info("The Raman settings changed — re-run to rebuild Image 2.")

        # ----------------------------------------------------------- Run
        st.subheader("5. Run")
        om_paths = {
            point: path
            for point, path in scan.image_files.get(state["magnification"] or "", {}).items()
        }
        has_content = bool(om_paths) or bool(scan.raman_files and raman_preset)

        if st.button("🔬 Run Analysis", type="primary", use_container_width=True,
                     disabled=not has_content):
            reset_results(state)
            try:
                with st.status("Running…", expanded=True) as status:
                    if om_paths:
                        st.write(f"Segmenting {len(om_paths)} optical frames…")
                        bar = st.progress(0.0)
                        frames = []
                        for done, point in enumerate(sorted(om_paths)):
                            frames.append(analyse_frame(
                                om_paths[point], point=point,
                                ref_label=state["reference_layer"],
                                name=f"{state['magnification']}-{point}",
                                # Only the fields the preset actually sets;
                                # everything else keeps contrast.py's default.
                                **optical.as_kwargs(),
                            ))
                            # Fraction of work finished, so the bar isn't full
                            # while the last (equally slow) frame is running.
                            bar.progress((done + 1) / len(om_paths))
                            state["frames"] = frames
                        # Two renders off one segmentation. The ~30 s of
                        # analysis is already spent; each render is about 5 s.
                        st.write("Building the OM figure…")
                        state["om_png"] = build_om_grid_figure(
                            frames, sample_name=scan.sample_name,
                            magnification=state["magnification"],
                            show_histograms=False,
                        )
                        st.write("Building the diagnostic copy…")
                        state["om_diagnostic_png"] = build_om_grid_figure(
                            frames, sample_name=scan.sample_name,
                            magnification=state["magnification"],
                            show_histograms=True,
                        )
                        state["optical_fingerprint"] = _optical_now

                    if scan.raman_files and raman_preset:
                        st.write(f"Fitting {len(scan.raman_files)} Raman files…")
                        bar = st.progress(0.0)
                        batch = run_sample_batch(
                            scan, raman_preset=raman_preset, pl_preset=None,
                            max_iterations=st.session_state.get("max_iterations", 2000),
                            progress_callback=lambda _label, done, total: bar.progress(
                                min(done / total, 1.0) if total else 1.0
                            ),
                        )
                        state["errors"] = batch.raman_errors
                        fitted = [(p, s.fit_result) for p, s in batch.raman_spectra]
                        pairs = filter_fits_by_quality(fitted)
                        # Both counts, not just the survivors: what the gate
                        # removed is reported in Results, and it cannot be
                        # recovered from `raman_stats` afterwards.
                        state["dropped"] = len(fitted) - len(pairs)
                        state["fitted"] = len(fitted)
                        if pairs:
                            st.write("Building the Raman figure…")
                            state["raman_stats"] = aggregate_fit_results(pairs)
                            state["raman_png"] = build_raman_quality_figure(
                                pairs, sample_name=scan.sample_name,
                                material_name=state["material"],
                            )
                            state["raman_fingerprint"] = _raman_now
                        # Nothing is said here about an empty `pairs`. Anything
                        # written inside this button block lives for exactly one
                        # rerun, and the operator's next interaction wipes it --
                        # which is how a run that produced no figure came to
                        # show only a bare exclusion count. The gate's verdict
                        # is reported from persisted state in Results instead.
                    status.update(label=f"{scan.sample_name} analysed", state="complete")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

# ---------------------------------------------------------------- Results
def _render_raman_gate_verdict() -> None:
    """Say what the quality gate did, on every rerun.

    Spectra dropped here are not fit failures, so they never reach the
    "failed to fit" list; they just leave, and `n` comes out smaller. When
    *every* spectrum is dropped there is no figure either, and a count on its
    own reads as a malfunction rather than as the verdict it is. The usual
    cause of a wholesale drop is a preset aimed at another material -- MoS2's
    383/408 cm-1 peaks on WSe2 data converge onto empty spectrum and score
    about -0.11 apiece -- so name the selected material and let the operator
    check it.
    """
    dropped = state.get("dropped") or 0
    if not dropped:
        return
    fitted = state.get("fitted") or 0
    if state.get("raman_png"):
        st.caption(
            f"{dropped} of {fitted} spectra fitted but scored "
            f"R² ≤ {R_SQUARED_MIN} and were excluded from the Raman figure "
            f"and statistics."
        )
    else:
        st.warning(
            f"**No Raman figure:** all {fitted} spectra fitted, and every one "
            f"scored R² ≤ {R_SQUARED_MIN}, so none reached the figure. The "
            f"usual cause is the wrong material — check that "
            f"**{state.get('material')}** is what this sample is."
        )


if state.get("om_png") or state.get("raman_png") or state.get("dropped"):
    st.markdown("---")

    if state.get("om_png"):
        st.subheader("Image 1 — OM analysis")
        frames = state["frames"] or []
        if frames:
            labels = frames[0].labels
            cols = st.columns(3)
            for col, label, (mean, std) in zip(cols, labels, class_summary(frames)):
                col.metric(label, f"{mean:.1f} %", f"± {std:.1f} %", delta_color="off")
        st.image(state["om_png"], use_container_width=True)

        if state.get("om_diagnostic_png"):
            # Collapsed: this copy is for deciding whether to trust the one
            # above, which is a question you ask only when something looks off.
            with st.expander("Diagnostic copy — green-channel histograms"):
                st.caption(
                    "Each frame's histogram with its mode and both thresholds "
                    "marked. Coverage percentages alone cannot show whether a "
                    "frame segmented sensibly; a saturated frame reads as a "
                    "clean wafer in the overlay and as a single spike here. "
                    "Internal review only — the clean copy above is the one a "
                    "report carries."
                )
                st.image(state["om_diagnostic_png"], use_container_width=True)

    if state.get("raman_png"):
        st.subheader("Image 2 — Raman analysis")
        st.image(state["raman_png"], use_container_width=True)

    _render_raman_gate_verdict()

    if state.get("errors"):
        with st.expander(f"{len(state['errors'])} spectra failed to fit"):
            for point, message in state["errors"][:50]:
                st.text(f"point {point}: {message}")

    st.subheader("Save Images")
    st.caption(
        "Saves one PNG per image, under the name you choose: `_OM` for the "
        "clean segmentation grid, `_OM_diagnostic` for the copy with "
        "histograms, `_Raman` for the quality panels."
    )
    if st.button("💾 Save Images As...", use_container_width=True):
        try:
            save_path = prompt_save_path(
                default_dir=state["folder"],
                default_filename=f"{state['scan'].sample_name}_QC.png",
                title="Save QC Images",
                filetypes=(("PNG images", "*.png"), ("All files", "*.*")),
                default_extension=".png",
            )
            if save_path:
                # One dialog, two files: the chosen name supplies the stem and
                # each image appends its own suffix, so the pair stays together
                # and neither can overwrite the other.
                base, _ext = os.path.splitext(save_path)
                saved_files = []
                for suffix, payload in (
                    ("OM", state.get("om_png")),
                    ("OM_diagnostic", state.get("om_diagnostic_png")),
                    ("Raman", state.get("raman_png")),
                ):
                    if payload:
                        target = f"{base}_{suffix}.png"
                        with open(target, "wb") as f:
                            f.write(payload)
                        saved_files.append(target)
                st.success("Saved:\n" + "\n".join(f"- {p}" for p in saved_files))
            # save_path is None => user cancelled => no-op
        except Exception as e:
            st.error(f"Failed to save: {e}")
