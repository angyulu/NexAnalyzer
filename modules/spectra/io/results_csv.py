"""
Fit-results CSV export: one row per fitted peak.

Four shapes, keyed to what the caller is holding:

- `export_fit_params_csv()` — the current spectrum only (sidebar Quick Export).
- `export_master_csv()` — every fitted file, plus provenance columns
  (auto-detected mode, X-range crop, convergence time) and, for PL, a leading
  "Raw" row per file. This is the batch/archival table.
- `export_point_fits_csv()` — one row per fitted peak per grid position, from
  bare `(point, FitResult)` pairs. The QC Panel's table: it keeps no
  `SpectrumFile` past the run, and a grid position is the unit it reports in.
- `export_peak_stats_csv()` — the aggregate the first three average to:
  `PeakStat` rows, mean +/- std +/- n per peak label.

All of them report Intensity — the fitted curve's maximum, via
`peak_metrics.peak_intensity_and_stderr` — not `FittedPeak.area`. See that
module for the two quantities and their names.
"""

from typing import Dict, List, Sequence, Tuple

import pandas as pd

from core.report.models import PeakStat

from ..models.peak import FitResult
from ..processing.peak_metrics import peak_intensity_and_stderr, raw_peak_stats

# Columns shared by both CSVs, in order.
_PEAK_COLUMNS = [
    "Peak_Label", "Center", "Center_Stderr", "Intensity", "Intensity_Stderr",
    "FWHM", "FWHM_Stderr", "Shape", "R_Squared", "Chi_Squared",
]


def _peak_row(filename: str, spectrum, peak) -> dict:
    """One fitted peak's row: identity, then the shared measurement columns."""
    intensity, intensity_stderr = peak_intensity_and_stderr(peak)
    return {
        "Filename": filename,
        "Mode": spectrum.mode,
        "Peak_Label": peak.label,
        "Center": peak.center,
        "Center_Stderr": peak.center_stderr,
        "Intensity": intensity,
        "Intensity_Stderr": intensity_stderr,
        "FWHM": peak.width_fwhm,
        "FWHM_Stderr": peak.width_stderr,
        "Shape": peak.shape,
        "R_Squared": spectrum.fit_result.r_squared,
        "Chi_Squared": spectrum.fit_result.chi_squared,
    }


def _provenance(spectrum) -> dict:
    """Master-CSV-only columns recording how the spectrum was processed."""
    return {
        "Auto_Detected": spectrum.auto_detected,
        "X_Range_Limited": spectrum.x_range_enabled,
        "X_Min": spectrum.x_min if spectrum.x_range_enabled else "",
        "X_Max": spectrum.x_max if spectrum.x_range_enabled else "",
    }


def _raw_row(filename: str, spectrum) -> dict:
    """PL-only leading row holding the unfitted spectrum's peak stats."""
    stats = raw_peak_stats(spectrum.processed_data.X, spectrum.processed_data.Y)
    row = {
        "Filename": filename,
        "Mode": spectrum.mode,
        **_provenance(spectrum),
        "Peak_Label": "Raw",
        "Center": stats.center,
        "Center_Stderr": "",
        "Intensity": stats.intensity,
        "Intensity_Stderr": "",
        "FWHM": stats.fwhm if stats.fwhm is not None else "",
        "FWHM_Stderr": "",
        "Shape": "",
        "R_Squared": "",
        "Chi_Squared": "",
        "Convergence_Time_s": "",
    }
    return row


def export_fit_params_csv(spectrum) -> str:
    """
    The current spectrum's fitted peak parameters as CSV.

    One row per fitted peak; no provenance columns and no PL Raw row (that's
    `export_master_csv`'s archival format).
    """
    rows = [
        _peak_row(spectrum.filename, spectrum, peak)
        for peak in spectrum.fit_result.fitted_peaks
    ]
    return pd.DataFrame(rows).to_csv(index=False)


def export_master_csv(files: Dict) -> str:
    """
    Every successfully fitted file's peaks in one table.

    Parameters
    ----------
    files : Dict[str, SpectrumFile]
        Mapping of filename -> SpectrumFile (i.e. st.session_state['files']).

    Returns
    -------
    str
        CSV content. A comment line if nothing has been fitted yet, so the
        file is never silently empty.
    """
    rows: List[dict] = []

    for filename, spectrum in files.items():
        if spectrum.fit_result is None or not spectrum.fit_result.success:
            continue

        if spectrum.mode == "PL" and len(spectrum.processed_data.Y) > 0:
            rows.append(_raw_row(filename, spectrum))

        for peak in spectrum.fit_result.fitted_peaks:
            rows.append({
                **_peak_row(filename, spectrum, peak),
                **_provenance(spectrum),
                "Convergence_Time_s": spectrum.fit_result.convergence_time,
            })

    if not rows:
        return "# No fit results to export\n"

    # Reindex so provenance columns land in a stable position even though the
    # Raw row and peak rows build their dicts in different orders.
    column_order = [
        "Filename", "Mode", "Auto_Detected", "X_Range_Limited", "X_Min", "X_Max",
        *_PEAK_COLUMNS, "Convergence_Time_s",
    ]
    return pd.DataFrame(rows)[column_order].to_csv(index=False)


def export_point_fits_csv(fits_by_point: Sequence[Tuple[int, FitResult]]) -> str:
    """
    One row per fitted peak per grid position, from `(point, FitResult)` pairs.

    Parameters
    ----------
    fits_by_point : Sequence[Tuple[int, FitResult]]
        The fits to tabulate, in the order they were produced. Pass the pairs
        that survived `filter_fits_by_quality`, not the raw batch: this table
        is meant to be the rows behind a stats table, and a reader who averages
        a column here must land on the number that stats table reports.

    Returns
    -------
    str
        CSV content, one row per peak. A comment line if there are no fits.

    Notes
    -----
    `Point` is not unique. One measurement point's file is commonly a map
    holding 25 or 100 spectra, each fitted separately, so `Spectrum` numbers
    them within their point in the order they were fitted — the same
    within-point grouping the aggregation treats as one position's spread.
    """
    rows: List[dict] = []
    seen: Dict[int, int] = {}

    for point, fit_result in fits_by_point:
        seen[point] = seen.get(point, 0) + 1
        for peak in fit_result.fitted_peaks:
            intensity, intensity_stderr = peak_intensity_and_stderr(peak)
            rows.append({
                "Point": point,
                "Spectrum": seen[point],
                "Peak_Label": peak.label,
                "Center": peak.center,
                "Center_Stderr": peak.center_stderr,
                "Intensity": intensity,
                "Intensity_Stderr": intensity_stderr,
                "FWHM": peak.width_fwhm,
                "FWHM_Stderr": peak.width_stderr,
                "Shape": peak.shape,
                "R_Squared": fit_result.r_squared,
                "Chi_Squared": fit_result.chi_squared,
            })

    if not rows:
        return "# No fit results to export\n"
    return pd.DataFrame(rows).to_csv(index=False)


def export_peak_stats_csv(stats: Sequence[PeakStat]) -> str:
    """
    Aggregated per-peak statistics as CSV: one row per peak label.

    The same `PeakStat` list the figures and report tables are built from,
    passed in rather than recomputed, so the CSV saved beside an image cannot
    disagree with it.

    `FWHM_v1` is deliberately absent. It is the pre-v3.4.0 Gaussian-only width
    kept for opt-in comparison only (see `FittedPeak.width_fwhm_v1`), and a
    column that quietly under-reports every width by 59-108% has no business
    appearing in a file that outlives the screen it was read on.

    Returns a comment line rather than an empty file when nothing aggregated.
    """
    if not stats:
        return "# No peak statistics to export\n"

    rows = [
        {
            "Peak_Label": stat.label,
            "N": stat.n,
            "Center_Mean": stat.center_mean,
            "Center_Std": stat.center_std,
            "Intensity_Mean": stat.intensity_mean,
            "Intensity_Std": stat.intensity_std,
            # None only for the empirical "Raw" row on a spectrum with no
            # half-maximum crossing. Blank, like the report dashes that cell.
            "FWHM_Mean": "" if stat.fwhm_mean is None else stat.fwhm_mean,
            "FWHM_Std": "" if stat.fwhm_std is None else stat.fwhm_std,
        }
        for stat in stats
    ]
    return pd.DataFrame(rows).to_csv(index=False)
