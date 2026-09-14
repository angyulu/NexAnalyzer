"""
The OM segmentation's numbers as CSV: two tables off one list of frames.

- `export_frame_stats_csv()` — one row per class, the mean +/- std the QC
  Panel's three metric tiles show. Three rows, for reading.
- `export_frame_points_csv()` — one row per frame, for pivoting and plotting.
  This is the detail the stats table averages away: the tiles say the film
  covered 71.2 +/- 5.8 %, this table says which position was the 5.8.

Both are built from the same `FrameResult` list the figures were drawn from,
so a CSV saved beside an image cannot describe a different segmentation.

Coverage percentages are a partition of the valid pixels and sum to 100 per
frame. Contrast is green-channel contrast *relative to the reference film*,
which is why the reference class has no contrast cell of its own.
"""

from typing import List, Sequence

import pandas as pd

from ..processing.contrast import FrameResult, class_summary, contrast_summary

#: Ordinal names for the three classes, independent of the reference layer.
#: `Class` carries the layer-aware label ("Below 2L", "Bilayer", "Above 2L");
#: `Position` stays stable across a 1L and a 2L sample, so two samples can be
#: stacked into one table without their class columns failing to line up.
_POSITIONS = ("Below", "Reference", "Above")


def export_frame_stats_csv(frames: Sequence[FrameResult]) -> str:
    """
    Per-class coverage and contrast across the frames, as CSV.

    Returns a comment line rather than an empty file when no frame segmented,
    so the saved file always says why it holds nothing.
    """
    if not frames:
        return "# No optical frames analysed\n"

    labels = frames[0].labels
    coverage = class_summary(frames)
    (below_contrast, above_contrast) = contrast_summary(frames)
    # The reference film is the contrast reference, so its own contrast is not
    # a number that exists. Blank, not 0.0, which would read as a measurement.
    contrast = (below_contrast, ("", ""), above_contrast)

    rows = [
        {
            "Class": label,
            "Position": position,
            "N_Frames": len(frames),
            "Coverage_Mean_pct": cov_mean,
            "Coverage_Std_pct": cov_std,
            "Contrast_Mean_pct": con_mean,
            "Contrast_Std_pct": con_std,
        }
        for label, position, (cov_mean, cov_std), (con_mean, con_std)
        in zip(labels, _POSITIONS, coverage, contrast)
    ]
    return pd.DataFrame(rows).to_csv(index=False)


def export_frame_points_csv(frames: Sequence[FrameResult]) -> str:
    """
    One row per segmented frame: its class coverages, contrasts, component
    counts, and the histogram landmarks the thresholds were placed from.

    The threshold columns are what the diagnostic image shows graphically. A
    frame that segmented badly is legible here as a mode pinned at saturation
    or a pair of thresholds sitting on top of each other, without having to
    open the PNG.
    """
    if not frames:
        return "# No optical frames analysed\n"

    rows: List[dict] = []
    for frame in sorted(frames, key=lambda f: f.point):
        below, reference, above = frame.percentages
        rows.append({
            "Point": frame.point,
            "Frame": frame.name,
            "Frame_Type": frame.frame_type,
            "Reference_Layer": frame.ref_label,
            "Below_Coverage_pct": below,
            "Reference_Coverage_pct": reference,
            "Above_Coverage_pct": above,
            "Below_Contrast_pct": frame.contrast_below,
            "Above_Contrast_pct": frame.contrast_above,
            "Below_Components": frame.components_below,
            "Above_Components": frame.components_above,
            "Green_Mode": frame.mode,
            "Sigma_Left": frame.sigma_l,
            "Sigma_Right": frame.sigma_r,
            "Sigma_Noise": frame.sigma_noise,
            "Threshold_Low": frame.threshold_low,
            "Threshold_High": frame.threshold_high,
            "Shoulder": frame.shoulder,
        })
    return pd.DataFrame(rows).to_csv(index=False)
