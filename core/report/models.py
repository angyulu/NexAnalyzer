"""
Data models for the QC Report feature: a folder-scan result describing a
9-point measurement grid (Raman/PL spectra + OM images), aggregated per-peak
fit statistics computed across a technique's 9 fits, and the per-class summary
of an optical segmentation.

These are the row and scan contracts a module fills in for the report
renderer. They live here, not in a technique package, because the renderer
draws Raman, PL and optical results side by side and `core` must stay unable
to import `modules`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional


@dataclass(frozen=True)
class SampleScan:
    """
    Result of scanning a sample folder for Raman/PL spectra and OM images.

    Attributes
    ----------
    folder : str
        Absolute path to the scanned folder.
    sample_name : str
        Folder's basename, used as the report title.
    raman_files : Dict[int, str]
        Point index -> absolute path, for files matching ``Raman_<N>.txt``.
    pl_files : Dict[int, str]
        Point index -> absolute path, for files matching ``PL_<N>.txt``.
    image_files : Dict[str, Dict[int, str]]
        Magnification label (e.g. "100x") -> {point index -> absolute path}.
    ignored_files : List[str]
        Basenames that matched none of the naming patterns above.
    """

    folder: str
    sample_name: str
    raman_files: Dict[int, str] = field(default_factory=dict)
    pl_files: Dict[int, str] = field(default_factory=dict)
    image_files: Dict[str, Dict[int, str]] = field(default_factory=dict)
    ignored_files: List[str] = field(default_factory=list)

    def magnifications(self) -> List[str]:
        """Magnification labels found, sorted alphabetically."""
        return sorted(self.image_files.keys())


RAW_STAT_LABEL = "Raw"
"""Label marking a `PeakStat` as the empirical row — measured off the spectrum
itself rather than produced by a fit. Reserved: the report renderer keys its
caption off it, and a fitted peak must never use it. The on-screen Fit Results
table and the master CSV label the same quantity the same way."""


@dataclass(frozen=True)
class PeakStat:
    """
    Mean/std/n of one fitted peak's parameters, aggregated across a
    technique's per-point fits (grouped by ``FittedPeak.label``).

    ``intensity_*`` is peak intensity — the maximum of the fitted component
    curve — the same quantity the CSV export and the on-screen Fit Results
    table call "Intensity". It is deliberately *not* ``FittedPeak.area``, the
    area lmfit solves for, which differs by a factor of FWHM x 1.064;
    reporting that here made the report disagree with every other surface while
    using the same column heading.

    ``fwhm_mean``/``fwhm_std`` are None only for a row whose width could not be
    measured — the empirical "Raw" row on a spectrum with no half-maximum
    crossing. The renderer dashes that cell rather than printing a 0.0 that
    would read as a measurement. Fitted peaks always have a width.

    ``fwhm_v1_mean``/``fwhm_v1_std`` are the pre-v3.4.0 Gaussian-only width
    (see ``FittedPeak.width_fwhm_v1``), aggregated the same way as
    ``fwhm_mean``/``fwhm_std``. Always None for the "Raw" row: it has no fit,
    so there is no sigma/gamma to compute the old formula from. Reporting
    surfaces show this only when a caller explicitly opts in — see
    ``build_summary_figure``'s and ``build_sample_results_xlsx``'s
    ``show_fwhm_v1`` parameter.
    """

    label: str
    n: int
    center_mean: float
    center_std: float
    intensity_mean: float
    intensity_std: float
    fwhm_mean: Optional[float]
    fwhm_std: Optional[float]
    fwhm_v1_mean: Optional[float] = None
    fwhm_v1_std: Optional[float] = None


class OpticalClassStat(NamedTuple):
    """One layer class's coverage and contrast, aggregated across a sample's
    segmented frames.

    The optical counterpart of `PeakStat`, and here for the same reason: the
    summary figure prints this table next to the Raman and PL ones, and `core`
    cannot import `modules.optical` to reach a `FrameResult`. The optical
    module builds these rows; the renderer only reads them.

    ``contrast_mean``/``contrast_std`` are None for the reference class, whose
    contrast is measured *against* it and so is not a number that exists. The
    renderer dashes that cell rather than printing a 0.0 that would read as a
    measurement — the same rule `PeakStat` uses for an unmeasurable width.

    """

    label: str
    coverage_mean: float
    coverage_std: float
    contrast_mean: Optional[float]
    contrast_std: Optional[float]
    n_frames: int
