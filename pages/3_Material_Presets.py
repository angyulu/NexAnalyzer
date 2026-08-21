"""
Material Presets page: create, edit, and delete the material presets used
by the Analysis page's Run Auto-Workflow / Run All Files buttons.

Presets are embedded in the app (src/presets/materials.json) as of v2.11.0,
replacing the earlier Excel-file workflow (presets/material_presets.xlsx).
This page is the only way to manage them now.
"""

import pandas as pd
import streamlit as st

from modules.spectra.models.preset import MaterialPreset, PeakTemplate
from modules.spectra.io.preset_store import load_presets, save_presets

PEAK_COLUMNS = ["peak_label", "center", "center_tolerance", "width_fwhm", "shape", "color"]
BASELINE_ALGORITHMS = ["Polynomial", "ALS", "None (Skip)"]
MODES = ["Raman", "PL"]


def _peaks_to_df(peak_templates: list[PeakTemplate]) -> pd.DataFrame:
    if not peak_templates:
        return pd.DataFrame(columns=PEAK_COLUMNS)
    return pd.DataFrame([t.to_dict() for t in peak_templates], columns=PEAK_COLUMNS)


def _df_to_peaks(df: pd.DataFrame) -> list[PeakTemplate]:
    peaks = []
    for _, row in df.iterrows():
        if pd.isna(row.get("peak_label")) or str(row.get("peak_label")).strip() == "":
            continue
        peaks.append(PeakTemplate(
            peak_label=str(row["peak_label"]).strip(),
            center=float(row["center"]),
            center_tolerance=float(row["center_tolerance"]),
            width_fwhm=float(row["width_fwhm"]),
            shape=float(row["shape"]),
            color=str(row["color"]).strip(),
        ))
    return peaks


def _render_preset_form(presets: dict, key_prefix: str, existing: MaterialPreset = None, original_key=None):
    """
    Render the editable fields for one preset (existing or new) and handle
    its Save/Delete buttons. Mutates `presets` and persists via
    save_presets() when the user saves or deletes.
    """
    d = existing  # shorthand

    col1, col2 = st.columns(2)
    with col1:
        material_name = st.text_input(
            "Material name", value=d.material_name if d else "", key=f"{key_prefix}_name"
        )
    with col2:
        mode = st.selectbox(
            "Mode", options=MODES,
            index=MODES.index(d.mode) if d else 0,
            key=f"{key_prefix}_mode"
        )

    col3, col4 = st.columns(2)
    with col3:
        despike_threshold = st.number_input(
            "Despike threshold", min_value=3.0, max_value=30.0,
            value=d.despike_threshold if d else 6.0, step=0.5,
            key=f"{key_prefix}_despike"
        )
    with col4:
        baseline_algorithm = st.selectbox(
            "Baseline algorithm", options=BASELINE_ALGORITHMS,
            index=BASELINE_ALGORITHMS.index(d.baseline_algorithm) if d else 0,
            key=f"{key_prefix}_baseline_algo"
        )

    baseline_degree = None
    baseline_lambda = None
    baseline_p = None
    if baseline_algorithm == "Polynomial":
        baseline_degree = st.number_input(
            "Baseline degree", min_value=1, max_value=10,
            value=d.baseline_degree if (d and d.baseline_degree) else 5, step=1,
            key=f"{key_prefix}_degree"
        )
    elif baseline_algorithm == "ALS":
        col5, col6 = st.columns(2)
        with col5:
            baseline_lambda = st.number_input(
                "ALS lambda", min_value=1000.0, max_value=1000000.0,
                value=d.baseline_lambda if (d and d.baseline_lambda) else 10000.0, step=1000.0,
                key=f"{key_prefix}_lambda"
            )
        with col6:
            baseline_p = st.number_input(
                "ALS p", min_value=0.001, max_value=0.1,
                value=d.baseline_p if (d and d.baseline_p) else 0.001, step=0.001,
                format="%.3f", key=f"{key_prefix}_p"
            )

    x_range_enabled = st.checkbox(
        "Limit X-range", value=d.x_range_enabled if d else False, key=f"{key_prefix}_xrange_enabled"
    )
    x_min = x_max = None
    if x_range_enabled:
        col7, col8 = st.columns(2)
        with col7:
            x_min = st.number_input(
                "X min", value=d.x_min if (d and d.x_min is not None) else 0.0, key=f"{key_prefix}_xmin"
            )
        with col8:
            x_max = st.number_input(
                "X max", value=d.x_max if (d and d.x_max is not None) else 1000.0, key=f"{key_prefix}_xmax"
            )

    exclusion_ranges = st.text_input(
        "Exclusion ranges (optional)",
        value=d.exclusion_ranges if (d and d.exclusion_ranges) else "",
        help="Semicolon-separated ranges to exclude from baseline fitting, e.g. '1200-1400; 2600-2800'",
        key=f"{key_prefix}_exclusion"
    )

    description = st.text_input(
        "Notes (optional)", value=d.description if d else "", key=f"{key_prefix}_description"
    )

    st.caption("Peak templates")
    peaks_df = st.data_editor(
        _peaks_to_df(d.peak_templates) if d else pd.DataFrame(columns=PEAK_COLUMNS),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "peak_label": st.column_config.TextColumn("Label", required=True),
            "center": st.column_config.NumberColumn("Center", required=True),
            "center_tolerance": st.column_config.NumberColumn("± Tolerance", required=True),
            "width_fwhm": st.column_config.NumberColumn("FWHM", required=True),
            "shape": st.column_config.NumberColumn("Shape (0=Gauss, 1=Lorentz)", min_value=0.0, max_value=1.0, required=True),
            "color": st.column_config.TextColumn("Color (#RRGGBB)", required=True),
        },
        key=f"{key_prefix}_peaks"
    )

    button_col1, button_col2 = st.columns([1, 1])
    with button_col1:
        save_clicked = st.button(
            "💾 Save" if d else "➕ Create Material",
            key=f"{key_prefix}_save", type="primary", use_container_width=True
        )
    with button_col2:
        delete_clicked = False
        if d:
            delete_clicked = st.button(
                "🗑️ Delete", key=f"{key_prefix}_delete", use_container_width=True
            )

    if delete_clicked:
        del presets[original_key]
        save_presets(presets)
        st.success(f"Deleted {original_key[0]} ({original_key[1]})")
        st.rerun()

    if save_clicked:
        new_key = (material_name.strip(), mode)

        if not material_name.strip():
            st.error("Material name is required.")
            return

        if new_key != original_key and new_key in presets:
            st.error(f"A preset for {new_key[0]} ({new_key[1]}) already exists.")
            return

        candidate = MaterialPreset(
            material_name=material_name.strip(),
            mode=mode,
            enabled=True,
            x_range_enabled=x_range_enabled,
            x_min=x_min,
            x_max=x_max,
            despike_threshold=float(despike_threshold),
            baseline_algorithm=baseline_algorithm,
            baseline_degree=int(baseline_degree) if baseline_degree is not None else None,
            baseline_lambda=float(baseline_lambda) if baseline_lambda is not None else None,
            baseline_p=float(baseline_p) if baseline_p is not None else None,
            exclusion_ranges=exclusion_ranges.strip() or None,
            peak_templates=_df_to_peaks(peaks_df),
            description=description.strip(),
        )

        errors = candidate.validate()
        if errors:
            for err in errors:
                st.error(err)
            return

        if original_key is not None and original_key != new_key:
            del presets[original_key]
        presets[new_key] = candidate
        save_presets(presets)
        st.success(f"Saved {new_key[0]} ({new_key[1]})")
        st.rerun()


st.title("🧪 Material Presets")
st.markdown(
    "Create and edit the material presets used by **Run Auto-Workflow** / "
    "**Run All Files** on the Analysis page."
)

presets = load_presets()
st.caption(f"{len(presets)} material(s) configured")

for key in sorted(presets.keys()):
    preset = presets[key]
    with st.expander(f"{preset.material_name} ({preset.mode})"):
        _render_preset_form(presets, key_prefix=f"edit_{key[0]}_{key[1]}", existing=preset, original_key=key)

st.markdown("---")
st.subheader("Add New Material")
with st.expander("➕ New material", expanded=len(presets) == 0):
    _render_preset_form(presets, key_prefix="new")
