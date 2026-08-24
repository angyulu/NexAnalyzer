"""
Weighted, staged progress for a long report build.

Report generation is a chain of stages with wildly different costs, and the
user's real question during it is "is this working, or has it died?". A bar
that reaches 100% and disappears while three quarters of the work is still
to come answers that question wrongly, which is what this exists to fix.

The weights below are **measured**, not guessed, on a real 9-point sample
(``Example/HADG06``: 9 Raman + 9 PL 2000-point spectra, 9x 2240x1680 BMP
optical images) totalling 24.5 s:

    fit 5.28s (21.5%) | Raman figures 3.98s (16.2%) | PL figures 4.66s (19.0%)
    optical images 5.37s (21.9%) | .pptx 2.09s (8.5%) | preview 3.17s (12.9%)

Don't flatten them to equal shares. Equal weights would put the bar at 50%
when 78% of the time is still ahead, which is the same lie in a different
shape. If the pipeline changes materially, re-measure rather than estimate.

Aggregation (stats, legends, ratios) is deliberately absent: it takes 4 ms,
so a visible step for it would flicker past and buy nothing.

This module is intentionally free of Streamlit. It computes fractions and
labels; the caller decides what to draw. That keeps the arithmetic — the part
with the off-by-one and the divide-by-zero in it — testable without a
browser or a script runner.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

# fraction in [0.0, 1.0], human-readable message
ProgressSink = Callable[[float, str], None]


@dataclass(frozen=True)
class Stage:
    """One phase of the build, and its measured share of the total wall time.

    ``weight`` is relative: `ReportProgress` renormalizes whatever set of
    stages it is handed, so a run with no PL files stays honest without the
    caller doing arithmetic.
    """

    key: str
    label: str
    weight: float


#: The full chain, in execution order, with measured weights. A caller keeps
#: only the stages its run will actually perform.
STAGES: Sequence[Stage] = (
    Stage("fit", "Fitting spectra", 0.215),
    Stage("raman_figures", "Rendering Raman figures", 0.162),
    Stage("pl_figures", "Rendering PL figures", 0.190),
    Stage("optical_images", "Loading optical images", 0.219),
    Stage("pptx", "Assembling the report", 0.085),
    Stage("preview", "Rendering preview in PowerPoint", 0.129),
)


def stages_for(
    *, has_raman: bool, has_pl: bool, has_optical: bool, has_preview: bool = True
) -> List[Stage]:
    """The stages a run will actually perform, in order.

    A sample with no PL files must not reserve 19% of the bar for PL figures;
    it would sit still through a stage that never runs. Dropping the stage and
    letting the remaining weights renormalize keeps the bar proportional to
    the work in front of it.
    """
    keep = {
        "fit": has_raman or has_pl,
        "raman_figures": has_raman,
        "pl_figures": has_pl,
        "optical_images": has_optical,
        "pptx": True,
        "preview": has_preview,
    }
    return [stage for stage in STAGES if keep.get(stage.key, False)]


class ReportProgress:
    """Drives a `ProgressSink` through a weighted sequence of stages.

    Usage is `start()` before a stage's work and, where the stage has
    countable sub-steps, `tick()` as they complete::

        progress.start("optical_images")
        for i, path in enumerate(paths, start=1):
            load(path)
            progress.tick("optical_images", i, len(paths))

    `start()` announcing *before* the work is the point: the label has to name
    the thing currently running, not the thing that just finished.
    """

    def __init__(self, stages: Sequence[Stage], sink: ProgressSink) -> None:
        if not stages:
            raise ValueError("stages must not be empty")

        total_weight = sum(stage.weight for stage in stages)
        if total_weight <= 0:
            raise ValueError(f"stage weights must sum to > 0 (got {total_weight})")

        self._stages: List[Stage] = list(stages)
        self._sink = sink

        # Renormalized so any subset of STAGES still spans exactly 0..1, and
        # cumulative offsets precomputed so `tick` is pure arithmetic.
        self._share: Dict[str, float] = {}
        self._offset: Dict[str, float] = {}
        running = 0.0
        for stage in self._stages:
            share = stage.weight / total_weight
            self._share[stage.key] = share
            self._offset[stage.key] = running
            running += share

        self._labels: Dict[str, str] = {s.key: s.label for s in self._stages}
        self._highest = 0.0  # the bar must never appear to go backwards

    @property
    def stage_keys(self) -> List[str]:
        return [stage.key for stage in self._stages]

    def _emit(self, fraction: float, message: str) -> None:
        # Streamlit raises if a progress value leaves [0.0, 1.0], and rounding
        # a sum of six renormalized floats can land a hair outside it.
        fraction = min(1.0, max(0.0, fraction))
        # Monotonic: a later stage's start must not undercut an earlier
        # stage's completed ticks, however the weights round.
        self._highest = max(self._highest, fraction)
        self._sink(self._highest, message)

    def _require(self, key: str) -> None:
        if key not in self._share:
            raise KeyError(
                f"unknown or inactive stage {key!r}; active stages are {self.stage_keys}"
            )

    def start(self, key: str, detail: str = "") -> None:
        """Announce a stage, before its work runs."""
        self._require(key)
        self._emit(self._offset[key], self.message(key, detail=detail))

    def tick(self, key: str, done: int, total: int, detail: str = "") -> None:
        """Report `done` of `total` sub-steps completed within a stage.

        A `total` of 0 means nothing to do, so the stage reads as complete
        rather than raising on the division.
        """
        self._require(key)
        completed = 1.0 if total <= 0 else min(1.0, max(0.0, done / total))
        fraction = self._offset[key] + completed * self._share[key]
        counted = detail or (f"{min(done, total)}/{total}" if total > 0 else "")
        self._emit(fraction, self.message(key, detail=counted))

    def complete(self, key: str, detail: str = "") -> None:
        """Mark a stage fully done without claiming the next one has begun."""
        self._require(key)
        self._emit(
            self._offset[key] + self._share[key], self.message(key, detail=detail)
        )

    def finish(self, message: str = "Report generated") -> None:
        self._emit(1.0, message)

    def message(self, key: str, detail: str = "") -> str:
        label = self._labels.get(key, key)
        return f"{label} ({detail})" if detail else f"{label}..."

    def sub_callback(
        self, key: str, totals: Optional[Dict[str, int]] = None
    ) -> Callable[[str, int, int], None]:
        """An adapter matching `sample_batch.ProgressCallback`.

        That callback is `(label, done, total)` and already fires once per
        fitted point, so the fitting stage gets per-point resolution for free
        rather than sitting still for its share of the bar.

        `totals` maps each label to the number of points it will report, and
        matters more than it looks: `run_sample_batch` runs the techniques in
        sequence and restarts its count for each, so Raman reporting 9/9 would
        fill the whole stage and PL would then report 1/9 — a lower fraction,
        which the monotonic guard pins in place. The bar would sit still
        through the entire second technique. Summing against a fixed combined
        denominator is what makes both halves visible. Pass None only when a
        single label reports.
        """
        self._require(key)
        combined = sum(totals.values()) if totals else 0
        seen: Dict[str, int] = {}

        def _callback(label: str, done: int, total: int) -> None:
            # max(): a stale lower report must not rewind this label's count.
            seen[label] = max(seen.get(label, 0), done)
            if combined > 0:
                self.tick(
                    key, sum(seen.values()), combined,
                    detail=f"{label} {min(done, total)}/{total}",
                )
            else:
                self.tick(key, done, total, detail=f"{label} {min(done, total)}/{total}")

        return _callback


def build(
    sink: ProgressSink,
    *,
    has_raman: bool,
    has_pl: bool,
    has_optical: bool,
    has_preview: bool = True,
) -> Optional[ReportProgress]:
    """A `ReportProgress` for a run with these techniques, or None if there is
    nothing to report on."""
    stages = stages_for(
        has_raman=has_raman,
        has_pl=has_pl,
        has_optical=has_optical,
        has_preview=has_preview,
    )
    if not stages:
        return None
    return ReportProgress(stages, sink)
