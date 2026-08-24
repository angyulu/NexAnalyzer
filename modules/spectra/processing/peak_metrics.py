"""
Metrics derived from a fit result: the per-peak numbers every reporting
surface displays, and their aggregation across a set of fits.

Two quantities, two names, used consistently everywhere:

- **intensity** — the fitted curve's maximum, via `peak_intensity_and_stderr`.
  This is what every reporting surface shows, because it's the number
  spectroscopists read off a plot: the on-screen Fit Results table, the
  exported CSVs, the Sample Report's summary tables and its LA/E2g+A1g ratio
  all agree on it.
- **area** — the area under the peak, `FittedPeak.area`, which is intensity x
  FWHM x 1.064 for a Voigt. It is what lmfit solves for and what lmfit itself
  calls "amplitude", which is exactly why it is named `area` here.

The two diverge whenever peaks have unequal widths: WSe2's LA mode is ~6x
broader than E2g+A1g, so their area ratio is ~4.3x their intensity ratio. The
Sample Report used to report area under an "Amplitude" heading while the CSV
used that same heading for intensity, and the two surfaces disagreed.

Don't reintroduce that. "Amplitude" names neither quantity anywhere in the
codebase; a caller that wants the integrated quantity takes `FittedPeak.area`
and labels it "area".
"""

from typing import List, NamedTuple, Optional, Tuple

import numpy as np

from ..models.peak import FitResult
from core.report.models import RAW_STAT_LABEL, PeakStat


def peak_intensity_and_stderr(peak) -> Tuple[float, float]:
    """
    A fitted peak's intensity and the standard error on that intensity.

    Intensity is the maximum of the fitted component curve, not
    `FittedPeak.area` (the area lmfit solves for). The reported stderr is
    `area_stderr` rescaled by the same intensity/area ratio — a linear
    approximation, but the only sensible one without re-propagating the
    covariance matrix.

    Falls back to the area and its stderr when no component curve was
    generated (e.g. a fit that converged without per-peak curves).
    """
    curve = getattr(peak, "component_curve", None)
    if curve is None or len(curve) == 0:
        return float(peak.area), float(peak.area_stderr)

    intensity = float(np.max(curve))
    if peak.area > 0:
        return intensity, float(peak.area_stderr) * (intensity / peak.area)
    return intensity, 0.0


def peak_intensity(peak) -> float:
    """A fitted peak's intensity — see peak_intensity_and_stderr()."""
    return peak_intensity_and_stderr(peak)[0]


class RawPeakStats(NamedTuple):
    """Fit-free stats read straight off a spectrum: the tallest point and the
    width of the spectrum at half that intensity. `fwhm` is None when the
    half-maximum crossing can't be measured (flat or non-positive signal)."""

    intensity: float
    center: float
    fwhm: Optional[float]


def raw_peak_stats(x: np.ndarray, y: np.ndarray) -> Optional[RawPeakStats]:
    """
    Measure the raw spectrum's dominant peak without reference to any fit.

    Used for PL, where the emission peak's raw intensity/position/width is
    reported alongside the fitted peaks — a sanity check on the fit and the
    number some instrument software quotes. Returns None for an empty
    spectrum.
    """
    if len(y) == 0:
        return None

    imax = int(np.argmax(y))
    intensity = float(y[imax])
    center = float(x[imax])

    fwhm: Optional[float] = None
    if intensity > 0:
        above = y >= intensity / 2.0
        if above.any():
            idxs = np.where(above)[0]
            fwhm = float(x[idxs[-1]] - x[idxs[0]])

    return RawPeakStats(intensity=intensity, center=center, fwhm=fwhm)


def aggregate_fit_results(fit_results: List[FitResult]) -> List[PeakStat]:
    """
    Group fitted peaks by label across `fit_results` and compute mean/std/n
    of center, intensity, and width_fwhm for each label.

    Intensity, not `FittedPeak.area` — see the module docstring.

    Label order follows first-seen order. Standard deviation uses ddof=1
    when n > 1, else 0.0 (a single point has no spread). Callers should
    pass only successful fits; `FitResult.success` is not checked here.
    """
    centers: dict = {}
    intensities: dict = {}
    fwhms: dict = {}
    order: List[str] = []

    for fit_result in fit_results:
        for peak in fit_result.fitted_peaks:
            if peak.label not in centers:
                centers[peak.label] = []
                intensities[peak.label] = []
                fwhms[peak.label] = []
                order.append(peak.label)
            centers[peak.label].append(peak.center)
            intensities[peak.label].append(peak_intensity(peak))
            fwhms[peak.label].append(peak.width_fwhm)

    stats = []
    for label in order:
        n = len(centers[label])
        ddof = 1 if n > 1 else 0
        stats.append(PeakStat(
            label=label,
            n=n,
            center_mean=float(np.mean(centers[label])),
            center_std=float(np.std(centers[label], ddof=ddof)) if n > 1 else 0.0,
            intensity_mean=float(np.mean(intensities[label])),
            intensity_std=float(np.std(intensities[label], ddof=ddof)) if n > 1 else 0.0,
            fwhm_mean=float(np.mean(fwhms[label])),
            fwhm_std=float(np.std(fwhms[label], ddof=ddof)) if n > 1 else 0.0,
        ))

    return stats


def aggregate_raw_peak_stats(spectra) -> Optional[PeakStat]:
    """
    The empirical PL measurement, aggregated across a sample's points: the
    tallest point of each processed spectrum, with no fit involved.

    Returned as a `PeakStat` labelled "Raw" so it drops straight into the
    report's summary table alongside the fitted peaks. This is the same
    fit-free quantity the on-screen Fit Results table and the master CSV
    already show as a "Raw" row; the three now agree.

    Read off `processed_data` — after de-spiking and baseline correction, the
    same layer the fit sees — so its intensity is comparable to the fitted
    intensities in the rows below it, not inflated by a baseline offset.

    `fwhm_mean`/`fwhm_std` are None when no point yielded a half-maximum
    crossing (`raw_peak_stats` returns None there). Averaging over the points
    that did measure would report a width from a subset while `n` claimed the
    full count, and defaulting to 0.0 would print a fake measurement, so the
    cell is dashed out instead.

    Returns None when no spectrum yields a raw peak at all.
    """
    intensities: List[float] = []
    centers: List[float] = []
    fwhms: List[float] = []

    for spectrum in spectra:
        data = getattr(spectrum, "processed_data", None)
        if data is None:
            continue
        raw = raw_peak_stats(data.X, data.Y)
        if raw is None:
            continue
        intensities.append(raw.intensity)
        centers.append(raw.center)
        if raw.fwhm is not None:
            fwhms.append(raw.fwhm)

    n = len(intensities)
    if n == 0:
        return None

    ddof = 1 if n > 1 else 0
    fwhm_mean = float(np.mean(fwhms)) if len(fwhms) == n else None
    if fwhm_mean is None:
        fwhm_std = None
    else:
        fwhm_std = float(np.std(fwhms, ddof=ddof)) if n > 1 else 0.0

    return PeakStat(
        label=RAW_STAT_LABEL,
        n=n,
        center_mean=float(np.mean(centers)),
        center_std=float(np.std(centers, ddof=ddof)) if n > 1 else 0.0,
        intensity_mean=float(np.mean(intensities)),
        intensity_std=float(np.std(intensities, ddof=ddof)) if n > 1 else 0.0,
        fwhm_mean=fwhm_mean,
        fwhm_std=fwhm_std,
    )


def compute_peak_intensity_ratio(
    fit_results: List[FitResult], numerator_label: str, denominator_label: str
) -> Optional[Tuple[float, float, int]]:
    """
    The per-point peak-intensity ratio `numerator_label` / `denominator_label`
    (e.g. "LA" / "E2g+A1g" for WSe2 Raman), summarized across `fit_results`.

    The ratio is formed per point first, then summarized — not
    mean(numerator) / mean(denominator) — so it describes the actual
    point-to-point ratio rather than a ratio of two separately averaged
    numbers. On a 9-point grid the two agree to well under a percent, but only
    the per-point form has a meaningful spread attached.

    Summarized by **median and median absolute deviation**, not mean and
    standard deviation: one badly fitted point moves a 9-point mean noticeably,
    and a ratio of two fitted quantities is exactly where that happens.

    Intensities, not `FittedPeak.area` — see the module docstring; for peaks
    of unequal width the two ratios differ by a large factor.

    Points missing either peak (or with a zero denominator) are skipped.
    Returns (median, mad, n), or None if no point has both peaks.
    """
    ratios = []
    for fit_result in fit_results:
        intensities = {peak.label: peak_intensity(peak) for peak in fit_result.fitted_peaks}
        numerator = intensities.get(numerator_label)
        denominator = intensities.get(denominator_label)
        if numerator is not None and denominator:
            ratios.append(numerator / denominator)

    if not ratios:
        return None

    values = np.asarray(ratios, dtype=float)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return (median, mad, len(ratios))
