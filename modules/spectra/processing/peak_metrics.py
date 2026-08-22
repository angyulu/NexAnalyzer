"""
Metrics derived from a fit result: the per-peak numbers every reporting
surface displays, and their aggregation across a set of fits.

Every reporting surface uses **height** — the fitted curve's maximum, via
`peak_height_and_stderr` — because it's the number spectroscopists read off a
plot. The on-screen Fit Results table, the exported CSVs, the Sample Report's
summary tables and its LA/E2g+A1g ratio all agree on it.

The other convention still exists on the model: `FittedPeak.amplitude` is
lmfit's own amplitude, i.e. **integrated intensity** — area under the peak,
height x FWHM x 1.064 for a Voigt. It is what the fitter solves for, and the
two diverge whenever peaks have unequal widths: WSe2's LA mode is ~6x broader
than E2g+A1g, so their area ratio is ~4.3x their height ratio. The Sample
Report used to report area under an "Amplitude" heading, which made it
disagree with the CSV that named the same column the same thing.

Don't reintroduce that. If a caller genuinely wants area, take
`FittedPeak.amplitude` explicitly and label it "integrated".
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
    of center, height, and width_fwhm for each label.

    Height, not lmfit's integrated amplitude — see the module docstring.

    Label order follows first-seen order. Standard deviation uses ddof=1
    when n > 1, else 0.0 (a single point has no spread). Callers should
    pass only successful fits; `FitResult.success` is not checked here.
    """
    centers: dict = {}
    heights: dict = {}
    fwhms: dict = {}
    order: List[str] = []

    for fit_result in fit_results:
        for peak in fit_result.fitted_peaks:
            if peak.label not in centers:
                centers[peak.label] = []
                heights[peak.label] = []
                fwhms[peak.label] = []
                order.append(peak.label)
            centers[peak.label].append(peak.center)
            heights[peak.label].append(peak_height(peak))
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
            height_mean=float(np.mean(heights[label])),
            height_std=float(np.std(heights[label], ddof=ddof)) if n > 1 else 0.0,
            fwhm_mean=float(np.mean(fwhms[label])),
            fwhm_std=float(np.std(fwhms[label], ddof=ddof)) if n > 1 else 0.0,
        ))

    return stats


def compute_peak_height_ratio(
    fit_results: List[FitResult], numerator_label: str, denominator_label: str
) -> Optional[Tuple[float, float, int]]:
    """
    The per-point peak-height ratio `numerator_label` / `denominator_label`
    (e.g. "LA" / "E2g+A1g" for WSe2 Raman), summarized across `fit_results`.

    The ratio is formed per point first, then summarized — not
    mean(numerator) / mean(denominator) — so it describes the actual
    point-to-point ratio rather than a ratio of two separately averaged
    numbers. On a 9-point grid the two agree to well under a percent, but only
    the per-point form has a meaningful spread attached.

    Summarized by **median and median absolute deviation**, not mean and
    standard deviation: one badly fitted point moves a 9-point mean noticeably,
    and a ratio of two fitted quantities is exactly where that happens.

    Heights, not lmfit's integrated amplitudes — see the module docstring; for
    peaks of unequal width the two ratios differ by a large factor.

    Points missing either peak (or with a zero denominator) are skipped.
    Returns (median, mad, n), or None if no point has both peaks.
    """
    ratios = []
    for fit_result in fit_results:
        heights = {peak.label: peak_height(peak) for peak in fit_result.fitted_peaks}
        numerator = heights.get(numerator_label)
        denominator = heights.get(denominator_label)
        if numerator is not None and denominator:
            ratios.append(numerator / denominator)

    if not ratios:
        return None

    values = np.asarray(ratios, dtype=float)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return (median, mad, len(ratios))
