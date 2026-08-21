"""
Metrics derived from a fit result: the per-peak numbers every reporting
surface displays, and their aggregation across a set of fits.

Two amplitude conventions coexist deliberately, so read carefully before
adding a caller:

- **height** (`peak_height_and_stderr`) — the fitted curve's maximum. This is
  what the on-screen Fit Results table and the exported CSVs report, because
  it's the number spectroscopists read off a plot.
- **integrated intensity** (`FittedPeak.amplitude`, used by
  `aggregate_fit_results` and `compute_peak_amplitude_ratio`) — lmfit's own
  amplitude, i.e. area under the peak (height x FWHM x 1.064 for a Voigt).
  This is what the Sample Report's summary tables and its LA/E2g+A1g ratio
  report.

Both are legitimate; they differ whenever peaks have unequal widths. Keeping
them in one module makes the choice explicit at each call site instead of
re-deriving either rule inline.
"""

from typing import List, NamedTuple, Optional, Tuple

import numpy as np

from ..models.peak import FitResult
from core.report.models import PeakStat


def peak_height_and_stderr(peak) -> Tuple[float, float]:
    """
    A fitted peak's height and the standard error on that height.

    Height is the maximum of the fitted component curve, not
    `FittedPeak.amplitude` (which lmfit reports as integrated intensity).
    The reported stderr is `amplitude_stderr` rescaled by the same
    height/amplitude ratio — a linear approximation, but the only sensible
    one without re-propagating the covariance matrix.

    Falls back to the raw amplitude and its stderr when no component curve
    was generated (e.g. a fit that converged without per-peak curves).
    """
    curve = getattr(peak, "component_curve", None)
    if curve is None or len(curve) == 0:
        return float(peak.amplitude), float(peak.amplitude_stderr)

    height = float(np.max(curve))
    if peak.amplitude > 0:
        return height, float(peak.amplitude_stderr) * (height / peak.amplitude)
    return height, 0.0


def peak_height(peak) -> float:
    """A fitted peak's height — see peak_height_and_stderr()."""
    return peak_height_and_stderr(peak)[0]


class RawPeakStats(NamedTuple):
    """Fit-free stats read straight off a spectrum: the tallest point and the
    width of the spectrum at half that height. `fwhm` is None when the
    half-maximum crossing can't be measured (flat or non-positive signal)."""

    intensity: float
    center: float
    fwhm: Optional[float]


def raw_peak_stats(x: np.ndarray, y: np.ndarray) -> Optional[RawPeakStats]:
    """
    Measure the raw spectrum's dominant peak without reference to any fit.

    Used for PL, where the emission peak's raw height/position/width is
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
    of center, amplitude, and width_fwhm for each label.

    Label order follows first-seen order. Standard deviation uses ddof=1
    when n > 1, else 0.0 (a single point has no spread). Callers should
    pass only successful fits; `FitResult.success` is not checked here.
    """
    centers: dict = {}
    amplitudes: dict = {}
    fwhms: dict = {}
    order: List[str] = []

    for fit_result in fit_results:
        for peak in fit_result.fitted_peaks:
            if peak.label not in centers:
                centers[peak.label] = []
                amplitudes[peak.label] = []
                fwhms[peak.label] = []
                order.append(peak.label)
            centers[peak.label].append(peak.center)
            amplitudes[peak.label].append(peak.amplitude)
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
            amplitude_mean=float(np.mean(amplitudes[label])),
            amplitude_std=float(np.std(amplitudes[label], ddof=ddof)) if n > 1 else 0.0,
            fwhm_mean=float(np.mean(fwhms[label])),
            fwhm_std=float(np.std(fwhms[label], ddof=ddof)) if n > 1 else 0.0,
        ))

    return stats


def compute_peak_amplitude_ratio(
    fit_results: List[FitResult], numerator_label: str, denominator_label: str
) -> Optional[Tuple[float, float, int]]:
    """
    Aggregate the per-point amplitude ratio `numerator_label` / `denominator_label`
    (e.g. "LA" / "E2g+A1g" for WSe2 Raman) across `fit_results`.

    The ratio is computed per point first, then averaged — not mean(numerator)
    / mean(denominator) — so it reflects the actual point-to-point ratio
    spread. Points missing either peak (or with a zero denominator) are
    skipped. Returns (mean, std, n), or None if no point has both peaks.
    """
    ratios = []
    for fit_result in fit_results:
        amplitudes = {peak.label: peak.amplitude for peak in fit_result.fitted_peaks}
        numerator = amplitudes.get(numerator_label)
        denominator = amplitudes.get(denominator_label)
        if numerator is not None and denominator:
            ratios.append(numerator / denominator)

    if not ratios:
        return None

    n = len(ratios)
    ddof = 1 if n > 1 else 0
    mean = float(np.mean(ratios))
    std = float(np.std(ratios, ddof=ddof)) if n > 1 else 0.0
    return (mean, std, n)
