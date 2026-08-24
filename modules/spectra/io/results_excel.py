"""
The Sample Report's numbers as a workbook: every point's fitted peaks, plus
the summary the slides show.

Three sheets, two audiences:

- ``Summary`` is the slide's tables — per-peak mean ± std for each technique,
  the intensity ratios, and any point that failed to fit — for reading.
- ``Raman`` and ``PL`` are tidy tables, one row per fitted peak per point,
  for pivoting and plotting. This is the detail the .pptx only ever shows
  aggregated: the deck says the E2g+A1g sat at 250.3 ± 0.4, the sheet says
  which point was the 0.4.

Every point that fitted is here, including the ones the summary averages over
silently; every point that didn't is named in the excluded block rather than
just missing, because a workbook that drops nine rows without saying so reads
as a complete record of a sample that was never measured that way.

Intensity is the fitted curve's maximum, via
``peak_metrics.peak_intensity_and_stderr`` — never ``FittedPeak.area``. Same
quantity under the same name as the on-screen table, both CSVs and the .pptx.
See peak_metrics for why those are two different numbers.

Cell values are written unrounded. The display formats below only decide how
many decimals Excel *shows*, so a user who widens a column's format gets the
rest of the number instead of digits we already discarded.
"""

import os
from io import BytesIO
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from openpyxl import Workbook
from openpyxl.styles import Font

from core.report.models import RAW_STAT_LABEL, PeakStat

from ..processing.peak_metrics import peak_intensity_and_stderr, raw_peak_stats

#: (median, MAD, n) — `peak_metrics.compute_peak_intensity_ratio`'s summary.
RatioSummary = Tuple[float, float, int]


class _Column(NamedTuple):
    """A column's heading, Excel number format, and width in characters."""

    header: str
    number_format: Optional[str] = None
    width: float = 12.0


class TechniqueResults(NamedTuple):
    """One technique's contribution to the workbook.

    ``stats`` is what the .pptx table shows, passed in rather than recomputed
    here, so the workbook cannot disagree with the deck written beside it —
    including PL's leading empirical row, which arrives as an ordinary
    `PeakStat` labelled `RAW_STAT_LABEL`.

    ``include_raw_row`` adds that same fit-free measurement per point on the
    data sheet. It is a flag, not an inference from ``label``, because which
    techniques want an empirical row is a reporting decision: PL's broad
    emission is read off the spectrum, Raman's modes are read off the fit.
    The master CSV draws the same line.
    """

    label: str
    point_spectra: Sequence[Tuple[int, object]] = ()
    stats: Optional[Sequence[PeakStat]] = None
    source_files: Optional[Dict[int, str]] = None
    errors: Sequence[Tuple[int, str]] = ()
    ratios: Sequence[Tuple[str, RatioSummary]] = ()
    include_raw_row: bool = False


# One row per fitted peak per point. Mode isn't a column: the sheet name is
# the mode, which is what keeps these tables pivotable as they stand.
_POINT_COLUMNS: Sequence[_Column] = (
    _Column("Point", "0", 7),
    _Column("Source_File", None, 24),
    _Column("Peak_Label", None, 14),
    _Column("Center", "0.00", 11),
    _Column("Center_Stderr", "0.000", 14),
    _Column("Intensity", "0.00", 12),
    _Column("Intensity_Stderr", "0.000", 17),
    _Column("FWHM", "0.00", 10),
    _Column("FWHM_Stderr", "0.000", 13),
    _Column("Shape", "0.00", 8),
    _Column("R_Squared", "0.0000", 11),
    _Column("Chi_Squared", "General", 13),
    _Column("Convergence_Time_s", "0.000", 19),
)

# Mean and std as separate numeric columns, not one "250.3 ± 0.4" string: the
# whole point of a workbook is that the next person can compute with it.
_SUMMARY_COLUMNS: Sequence[_Column] = (
    _Column("Peak", None, 16),
    _Column("N", "0", 5),
    _Column("Center_Mean", "0.00", 13),
    _Column("Center_Std", "0.000", 12),
    _Column("Intensity_Mean", "0.00", 15),
    _Column("Intensity_Std", "0.000", 14),
    _Column("FWHM_Mean", "0.00", 12),
    _Column("FWHM_Std", "0.000", 11),
)

_RATIO_COLUMNS: Sequence[_Column] = (
    _Column("Ratio", None, 22),
    _Column("N", "0", 5),
    _Column("Median", "0.000", 11),
    _Column("MAD", "0.000", 11),
)

_EXCLUDED_COLUMNS: Sequence[_Column] = (
    _Column("Technique", None, 12),
    _Column("Point", "0", 7),
    _Column("Error", None, 60),
)

_HEADING_FONT = Font(bold=True)
_TITLE_FONT = Font(bold=True, size=14)


def _point_rows(technique: TechniqueResults) -> List[list]:
    """`technique`'s data-sheet rows, ordered by point then by fit order."""
    source_files = technique.source_files or {}
    rows: List[list] = []

    for point, spectrum in sorted(technique.point_spectra, key=lambda item: item[0]):
        source = os.path.basename(source_files.get(point, "")) or None
        fit = spectrum.fit_result

        if technique.include_raw_row:
            raw = raw_peak_stats(spectrum.processed_data.X, spectrum.processed_data.Y)
            # `raw` is None only for an empty spectrum — no row at all then.
            # `raw.fwhm` is None whenever there's no half-maximum crossing (a
            # flat or non-positive signal), and that cell is left empty rather
            # than filled with a 0.0 that would read as a measured width. The
            # intensity is still reported: 0 counts is a measurement.
            if raw is not None:
                rows.append([
                    point, source, RAW_STAT_LABEL,
                    raw.center, None, raw.intensity, None, raw.fwhm, None,
                    None, None, None, None,
                ])

        for peak in (fit.fitted_peaks if fit else []):
            intensity, intensity_stderr = peak_intensity_and_stderr(peak)
            rows.append([
                point, source, peak.label,
                peak.center, peak.center_stderr,
                intensity, intensity_stderr,
                peak.width_fwhm, peak.width_stderr,
                peak.shape, fit.r_squared, fit.chi_squared, fit.convergence_time,
            ])

    return rows


def _summary_rows(stats: Optional[Sequence[PeakStat]]) -> List[list]:
    return [
        [
            stat.label, stat.n,
            stat.center_mean, stat.center_std,
            stat.intensity_mean, stat.intensity_std,
            # None for a row whose width genuinely couldn't be measured — the
            # same cell the .pptx dashes out.
            stat.fwhm_mean, stat.fwhm_std,
        ]
        for stat in (stats or [])
    ]


def _summary_caption(technique: TechniqueResults) -> str:
    """Mirrors the .pptx caption rule: a table led by the empirical row is not
    a "fit summary"."""
    has_empirical = any(stat.label == RAW_STAT_LABEL for stat in (technique.stats or []))
    kind = (
        "summary (empirical + fitted, mean ± std)" if has_empirical
        else "fit summary (mean ± std)"
    )
    return f"{technique.label} {kind}"


def _write_table(
    ws, columns: Sequence[_Column], rows: Sequence[Sequence], start_row: int = 1
) -> int:
    """Write a header row and `rows` beneath it; return the next free row."""
    for col_index, column in enumerate(columns, start=1):
        cell = ws.cell(row=start_row, column=col_index, value=column.header)
        cell.font = _HEADING_FONT

    for row_offset, row in enumerate(rows, start=1):
        for col_index, (column, value) in enumerate(zip(columns, row), start=1):
            cell = ws.cell(row=start_row + row_offset, column=col_index, value=value)
            # Guarded on the value's type: a format applied to the empty cell of
            # an unmeasured width would make Excel render it as 0.00.
            if column.number_format and isinstance(value, (int, float)):
                cell.number_format = column.number_format

    return start_row + len(rows) + 1


def _set_widths(ws, columns: Sequence[_Column]) -> None:
    for col_index, column in enumerate(columns, start=1):
        letter = ws.cell(row=1, column=col_index).column_letter
        ws.column_dimensions[letter].width = column.width


def _add_data_sheet(wb: Workbook, technique: TechniqueResults) -> None:
    """One technique's per-point sheet, or nothing when it produced no fits —
    an empty sheet named "PL" claims a technique that was never measured."""
    rows = _point_rows(technique)
    if not rows:
        return

    ws = wb.create_sheet(title=technique.label)
    _write_table(ws, _POINT_COLUMNS, rows)
    _set_widths(ws, _POINT_COLUMNS)
    # The header stays put while scrolling 9 points x n peaks, and the filter
    # is how you pull one peak's row out of every point in two clicks.
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _add_summary_sheet(
    wb: Workbook,
    sample_name: str,
    material_name: str,
    report_date: str,
    techniques: Sequence[TechniqueResults],
) -> None:
    """The reading sheet: identity block, then each technique's summary table
    and ratios, then whatever was excluded."""
    ws = wb.create_sheet(title="Summary", index=0)

    ws["A1"] = "NexAnalyzer sample results"
    ws["A1"].font = _TITLE_FONT

    row = 3
    for label, value in (
        ("Sample", sample_name),
        ("Material", material_name),
        ("Date", report_date),
    ):
        ws.cell(row=row, column=1, value=label).font = _HEADING_FONT
        ws.cell(row=row, column=2, value=value)
        row += 1
    row += 1

    for technique in techniques:
        if technique.stats:
            ws.cell(row=row, column=1, value=_summary_caption(technique)).font = _HEADING_FONT
            row = _write_table(
                ws, _SUMMARY_COLUMNS, _summary_rows(technique.stats), start_row=row + 1
            )
            row += 1

        if technique.ratios:
            ws.cell(
                row=row, column=1,
                value=f"{technique.label} intensity ratios (median ± MAD)",
            ).font = _HEADING_FONT
            ratio_rows = [
                [label, n, median, mad] for label, (median, mad, n) in technique.ratios
            ]
            row = _write_table(ws, _RATIO_COLUMNS, ratio_rows, start_row=row + 1)
            row += 1

    excluded = [
        [technique.label, point, message]
        for technique in techniques
        for point, message in technique.errors
    ]
    if excluded:
        ws.cell(
            row=row, column=1,
            value=f"Excluded — {len(excluded)} point(s) failed to fit and are absent above",
        ).font = _HEADING_FONT
        _write_table(ws, _EXCLUDED_COLUMNS, excluded, start_row=row + 1)

    # Widths from the summary table: the blocks share the sheet's columns, and
    # it is the one whose headings are long enough to need them.
    _set_widths(ws, _SUMMARY_COLUMNS)


def build_sample_results_xlsx(
    *,
    sample_name: str,
    material_name: str,
    report_date: str,
    techniques: Sequence[TechniqueResults],
) -> bytes:
    """
    The sample's fit results as .xlsx bytes: a `Summary` sheet, then one
    per-point sheet for each technique that produced fits.

    The identity arguments mirror the .pptx builder's, so the two artifacts
    written side by side name the same sample, material and date.

    Returns
    -------
    bytes
        A workbook ready to write to disk. It always carries a Summary sheet,
        even for a sample where nothing fitted — the metadata and the excluded
        list are then the whole record, which beats an absent file.
    """
    wb = Workbook()
    # A fresh Workbook arrives with one unnamed sheet; the real ones are
    # created with their titles below.
    wb.remove(wb.active)

    _add_summary_sheet(wb, sample_name, material_name, report_date, techniques)
    for technique in techniques:
        _add_data_sheet(wb, technique)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
