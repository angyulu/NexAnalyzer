"""
The OM segmentation's numbers as tables: two shapes off one list of frames.

- `frame_class_stats()` — one row per class, the mean +/- std the QC Report's
  three metric tiles and its summary page's OM table show. Three rows, for
  reading.
- `frame_point_rows()` — one row per frame, for pivoting and plotting. This is
  the detail the class table averages away: the tiles say the film covered
  71.2 +/- 5.8 %, this table says which position was the 5.8.

Both are built from the same `FrameResult` list the figures were drawn from,
so the workbook saved beside an image cannot describe a different
segmentation.

Rows, not CSV text. Until v5.0.0 this module wrote two CSV files that were
saved next to the QC Panel's PNGs; the QC Report writes one workbook, so the
rows go into sheets and the formatting decisions belong to whatever renders
them. `frame_class_stats` returns `core.report.models.OpticalClassStat` — the
contract lives in `core` because the summary figure prints this table beside
the Raman and PL ones and `core` cannot import `modules`.

Coverage percentages are a partition of the valid pixels and sum to 100 per
frame. Contrast is green-channel contrast *relative to the reference film*,
which is why the reference class has no contrast of its own.

Both tables carry the histogram landmarks the thresholds were placed from, so
a frame that segmented badly is legible without opening the PNG.
"""

from typing import List, Optional, Sequence, Tuple

from core.report.models import OpticalClassStat

from ..processing.contrast import FrameResult, class_summary, contrast_summary

#: Ordinal names for the three classes, independent of the reference layer.
#: The class label is layer-aware ("Below 2L", "Bilayer", "Above 2L"); this
#: stays stable across a 1L and a 2L sample, so two samples can be stacked into
#: one table without their class columns failing to line up.
POSITIONS = ("Below", "Reference", "Above")

#: Per-frame column headers, in order, matching `frame_point_rows`. Named here
#: because this module owns the schema; the workbook looks up formats and
#: widths against these.
POINT_COLUMNS: Tuple[str, ...] = (
    "Point", "Frame", "Frame_Type", "Reference_Layer",
    "Below_Coverage_pct", "Reference_Coverage_pct", "Above_Coverage_pct",
    "Below_Contrast_pct", "Above_Contrast_pct",
    "Below_Components", "Above_Components",
    "Green_Mode", "Sigma_Left", "Sigma_Right", "Sigma_Noise",
    "Threshold_Low", "Threshold_High", "Shoulder",
)

#: Per-class column headers, in order, matching `frame_class_rows`.
CLASS_COLUMNS: Tuple[str, ...] = (
    "Class", "Position", "N_Frames",
    "Coverage_Mean_pct", "Coverage_Std_pct",
    "Contrast_Mean_pct", "Contrast_Std_pct",
)


def frame_class_stats(frames: Sequence[FrameResult]) -> List[OpticalClassStat]:
    """Per-class coverage and contrast across the frames.

    Returns an empty list when no frame segmented, which the renderers read as
    "no table" rather than as a table of zeros.
    """
    if not frames:
        return []

    labels = frames[0].labels
    coverage = class_summary(frames)
    (below_contrast, above_contrast) = contrast_summary(frames)
    # The reference film is the contrast reference, so its own contrast is not
    # a number that exists. None, not 0.0, which would read as a measurement.
    contrast: Tuple[Optional[Tuple[float, float]], ...] = (
        below_contrast, None, above_contrast
    )

    return [
        OpticalClassStat(
            label=label,
            coverage_mean=cov[0],
            coverage_std=cov[1],
            contrast_mean=None if con is None else con[0],
            contrast_std=None if con is None else con[1],
            n_frames=len(frames),
        )
        for label, cov, con in zip(labels, coverage, contrast)
    ]


def frame_class_rows(frames: Sequence[FrameResult]) -> List[list]:
    """`frame_class_stats` as rows aligned to `CLASS_COLUMNS`.

    `Position` is carried here but not on `OpticalClassStat`: it exists to make
    two samples stackable in a spreadsheet, which is a table concern rather
    than something the summary figure draws.
    """
    return [
        [
            entry.label, position, entry.n_frames,
            entry.coverage_mean, entry.coverage_std,
            entry.contrast_mean, entry.contrast_std,
        ]
        for entry, position in zip(frame_class_stats(frames), POSITIONS)
    ]


def frame_point_rows(frames: Sequence[FrameResult]) -> List[list]:
    """One row per segmented frame, aligned to `POINT_COLUMNS`.

    Its class coverages, contrasts, component counts, and the histogram
    landmarks the thresholds were placed from. The threshold columns are what
    the diagnostic image shows graphically: a frame that segmented badly is
    legible here as a mode pinned at saturation or a pair of thresholds sitting
    on top of each other, without having to open the PNG.
    """
    rows: List[list] = []
    for frame in sorted(frames, key=lambda f: f.point):
        below, reference, above = frame.percentages
        rows.append([
            frame.point, frame.name, frame.frame_type, frame.ref_label,
            below, reference, above,
            frame.contrast_below, frame.contrast_above,
            frame.components_below, frame.components_above,
            frame.mode, frame.sigma_l, frame.sigma_r, frame.sigma_noise,
            frame.threshold_low, frame.threshold_high, frame.shoulder,
        ])
    return rows
