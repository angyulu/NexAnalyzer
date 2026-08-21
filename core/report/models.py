"""
Data models for the Sample Report feature: a folder-scan result describing
a 9-point measurement grid (Raman/PL spectra + OM images), and aggregated
per-peak fit statistics computed across a technique's 9 fits.
"""

from dataclasses import dataclass, field
from typing import Dict, List


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


@dataclass(frozen=True)
class PeakStat:
    """
    Mean/std/n of one fitted peak's parameters, aggregated across a
    technique's per-point fits (grouped by ``FittedPeak.label``).
    """

    label: str
    n: int
    center_mean: float
    center_std: float
    amplitude_mean: float
    amplitude_std: float
    fwhm_mean: float
    fwhm_std: float
