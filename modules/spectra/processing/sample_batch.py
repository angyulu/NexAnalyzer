"""
Per-sample batch-fit orchestration for the Sample Report feature: loads
and fits every discovered Raman/PL file against its technique's preset,
reusing execute_auto_workflow() per file (same as "Run All Files" on the
Analysis page, just headless and grouped by point index).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from ..models.preset import MaterialPreset
from core.report.models import SampleScan
from ..models.spectrum import ProcessingSettings, SpectrumFile
from .auto_workflow import execute_auto_workflow
from .parser import parse_spectrum

ProgressCallback = Callable[[str, int, int], None]


@dataclass
class SampleBatchResult:
    raman_spectra: List[Tuple[int, SpectrumFile]] = field(default_factory=list)
    pl_spectra: List[Tuple[int, SpectrumFile]] = field(default_factory=list)
    raman_errors: List[Tuple[int, str]] = field(default_factory=list)
    pl_errors: List[Tuple[int, str]] = field(default_factory=list)


def _run_one_technique(
    files_by_point: Dict[int, str],
    mode: str,
    preset: Optional[MaterialPreset],
    max_iterations: int,
    out_spectra: List[Tuple[int, SpectrumFile]],
    out_errors: List[Tuple[int, str]],
    progress_callback: Optional[ProgressCallback],
) -> None:
    """Load + fit every point in `files_by_point` against `preset`.

    A `preset` of None skips the technique entirely (no entries added to
    either output list, callback never invoked). A parse or fit failure for
    one point is recorded in `out_errors` and excluded from `out_spectra`;
    this never raises.
    """
    if preset is None:
        return

    points = sorted(files_by_point.keys())
    total = len(points)
    for done, point in enumerate(points, start=1):
        filepath = files_by_point[point]
        try:
            spectrum_data = parse_spectrum(filepath)
            spectrum_file = SpectrumFile(
                filename=f"{mode}_{point}",
                mode=mode,
                original_data=spectrum_data,
                raw_data=spectrum_data,
                processed_data=spectrum_data,
                processing_settings=ProcessingSettings(),
            )
            result = execute_auto_workflow(spectrum_file, preset, max_iterations=max_iterations)
            if result["success"]:
                out_spectra.append((point, spectrum_file))
            else:
                out_errors.append((point, result.get("error_message", "Unknown error")))
        except Exception as e:
            out_errors.append((point, str(e)))

        if progress_callback is not None:
            progress_callback(mode, done, total)


def run_sample_batch(
    scan: SampleScan,
    raman_preset: Optional[MaterialPreset],
    pl_preset: Optional[MaterialPreset],
    max_iterations: int = 2000,
    progress_callback: Optional[ProgressCallback] = None,
) -> SampleBatchResult:
    """
    Fit every discovered Raman/PL file in `scan` against its respective
    preset. A preset of None for a technique skips it entirely. A parse or
    fit failure for one point is recorded in the matching `*_errors` list
    and excluded from `*_spectra`; this never raises.
    """
    result = SampleBatchResult()

    _run_one_technique(
        scan.raman_files, "Raman", raman_preset, max_iterations,
        result.raman_spectra, result.raman_errors, progress_callback
    )
    _run_one_technique(
        scan.pl_files, "PL", pl_preset, max_iterations,
        result.pl_spectra, result.pl_errors, progress_callback
    )

    return result
