"""
Image 2 of the QC Panel: the Raman quality panels.

Reproduces the inherited WSe2 Raman figure — a 2x3 grid whose columns are
metric families (FWHM, peak centres, diagnostic ratios) and whose rows are the
peaks within each family. Every panel is a strip plot across the sample's grid
positions: the individual fits as a jittered cloud, a mean +/- std marker per
position, and the pooled median as a dashed line.

The grey reference lines are **specs**. They come from the inherited analysis,
where the wafer-comparison scripts label them literally "FWHM = 7 (Spec)" and
"Ratio = 0.13 (Spec)". They are drawn and never evaluated — this figure reports,
it does not judge. Anyone adding a pass/fail verdict needs to decide first what
the rule is (pooled median across the line? any position's mean? a fraction of
individual fits?), and that decision is not encoded here.

Outlier handling matches `peak_metrics.aggregate_fit_results` exactly: the same
R-squared gate upstream, the same 1.5x IQR cut within each position. That is
deliberate and load-bearing — this figure and the report's summary tables show
the same quantities, so a difference in cleaning would put two different numbers
for one measurement in front of the same reader.
"""

import io
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

import matplotlib

matplotlib.use("Agg")  # no display; must precede the pyplot import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import gridspec  # noqa: E402

from ..models.peak import FitResult  # noqa: E402
from ..processing.peak_metrics import iqr_mask, peak_intensity  # noqa: E402

#: Plotly's qualitative sequence, carried over from the inherited scripts so a
#: position keeps the colour it has in the reports people already read. Cycled
#: by index, so more than eleven positions repeat rather than fail.
POSITION_COLORS = (
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52", "#1CBE4F",
)

_FS_SUPTITLE = 18
_FS_TITLE = 15
_FS_LABEL = 13
_FS_PANEL = 13
_FS_TICK = 12
_FS_REFTEXT = 11

_JITTER = 0.18
_MARKER_OFFSET = 0.28


@dataclass(frozen=True)
class PeakPanel:
    """One panel plotting a fitted parameter of a single peak."""

    peak: str
    metric: str          # "center" | "fwhm" | "intensity"
    ylabel: str
    caption: str
    spec: Optional[float] = None


@dataclass(frozen=True)
class RatioPanel:
    """One panel plotting a per-spectrum intensity ratio of two peaks."""

    numerator: str
    denominator: str
    ylabel: str
    caption: str
    spec: Optional[float] = None


Panel = Union[PeakPanel, RatioPanel]

#: The figure, as data. Three columns of two panels; column order and titles
#: match the inherited script so the output is recognisable to people already
#: reading these reports.
PANEL_COLUMNS: Tuple[Tuple[str, Tuple[Panel, Panel]], ...] = (
    ("FWHM", (
        PeakPanel("E2g+A1g", "fwhm", "FWHM (cm⁻¹)", "E₂g + A₁g", spec=7.0),
        PeakPanel("2LA", "fwhm", "FWHM (cm⁻¹)", "2LA(M)"),
    )),
    ("Peak Centers", (
        PeakPanel("E2g+A1g", "center", "Raman shift (cm⁻¹)", "E₂g + A₁g center"),
        PeakPanel("B2g", "center", "Raman shift (cm⁻¹)", "B₂g center", spec=308.0),
    )),
    ("Diagnostic Ratios", (
        RatioPanel("LA", "E2g+A1g", "I(LA) / I(E₂g+A₁g)", "Defect ratio", spec=0.13),
        RatioPanel("C", "LB", "I(C) / I(LB)", "Stacking ratio"),
    )),
)


def _peak_values(fits_by_point, panel: PeakPanel) -> Dict[int, np.ndarray]:
    out: Dict[int, list] = {}
    for point, fit in fits_by_point:
        for peak in fit.fitted_peaks:
            if peak.label != panel.peak:
                continue
            if panel.metric == "center":
                value = peak.center
            elif panel.metric == "fwhm":
                value = peak.width_fwhm
            else:
                value = peak_intensity(peak)
            out.setdefault(point, []).append(value)
    return {p: np.asarray(v, float) for p, v in out.items()}


def _ratio_values(fits_by_point, panel: RatioPanel) -> Dict[int, np.ndarray]:
    """Ratios formed within one spectrum, then collected by position.

    Per spectrum first, never mean(numerator)/mean(denominator): only the
    per-spectrum form has a spread that means anything.
    """
    out: Dict[int, list] = {}
    for point, fit in fits_by_point:
        intensities = {p.label: peak_intensity(p) for p in fit.fitted_peaks}
        numerator = intensities.get(panel.numerator)
        denominator = intensities.get(panel.denominator)
        if numerator is not None and denominator:
            out.setdefault(point, []).append(numerator / denominator)
    return {p: np.asarray(v, float) for p, v in out.items()}


def _draw_panel(ax, by_point: Dict[int, np.ndarray], positions: Sequence[int],
                panel: Panel, is_bottom: bool, rng: np.random.Generator) -> None:
    pooled = []
    for index, position in enumerate(positions):
        values = by_point.get(position)
        if values is None or values.size == 0:
            continue
        clean = values[iqr_mask(values)]
        if clean.size == 0:
            continue
        colour = POSITION_COLORS[index % len(POSITION_COLORS)]
        jitter = position + rng.uniform(-_JITTER, _JITTER, size=clean.size)
        ax.scatter(jitter, clean, color=colour, s=18, alpha=0.5,
                   edgecolor="none", zorder=3)
        std = clean.std(ddof=1) if clean.size > 1 else 0.0
        ax.errorbar(position + _MARKER_OFFSET, clean.mean(), yerr=std,
                    fmt="s", color=colour, ecolor=colour, elinewidth=2,
                    capsize=4, capthick=2, markersize=8, markerfacecolor=colour,
                    markeredgecolor=colour, markeredgewidth=1.2, zorder=5)
        pooled.extend(clean.tolist())

    if pooled:
        median = float(np.median(pooled))
        ax.axhline(median, color="black", linestyle="--", linewidth=1.3,
                   alpha=0.8, zorder=2, label=f"Median = {median:.2f}")
        ax.legend(loc="upper right", fontsize=_FS_REFTEXT, framealpha=0.85)
    else:
        ax.text(0.5, 0.5, f"no {getattr(panel, 'peak', 'data')} fits",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=_FS_LABEL, color="#999999")

    if panel.spec is not None:
        ax.axhline(panel.spec, color="grey", linewidth=1.2, alpha=0.6, zorder=1)
        # Value at the right edge in axes-fraction x, data y, so it tracks the
        # line without a second legend entry competing with the median's.
        ax.text(1.005, panel.spec, f"{panel.spec:g}", transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=_FS_REFTEXT, color="grey")

    ax.text(0.02, 0.95, panel.caption, transform=ax.transAxes, va="top", ha="left",
            fontsize=_FS_PANEL, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, lw=0))

    ax.set_ylabel(panel.ylabel, fontsize=_FS_LABEL)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_xticks(list(positions))
    ax.tick_params(axis="both", labelsize=_FS_TICK)
    ax.set_xlim(min(positions) - 0.7, max(positions) + 0.8)
    if is_bottom:
        ax.set_xlabel("Position", fontsize=_FS_LABEL)
    else:
        ax.tick_params(labelbottom=False)


def build_raman_quality_figure(
    fits_by_point: Sequence[Tuple[int, FitResult]],
    sample_name: str,
    material_name: str = "WSe₂",
    dpi: int = 160,
) -> bytes:
    """
    Render the Raman quality figure and return it as PNG bytes.

    `fits_by_point` is `(position, FitResult)` pairs, already passed through
    `peak_metrics.filter_fits_by_quality`; this applies only the per-position
    IQR cut on top, matching the aggregation the summary tables use.

    Returns bytes rather than a Figure so a caller cannot leak the canvas.
    """
    if not fits_by_point:
        raise ValueError("build_raman_quality_figure needs at least one fit")

    positions = sorted({point for point, _ in fits_by_point})
    spectra = len(fits_by_point)

    # Seeded per panel rather than once for the figure: the inherited script
    # draws jitter from one module-level generator consumed in panel order, so
    # inserting or reordering a panel silently moves every later panel's cloud.
    fig = plt.figure(figsize=(22, 11), dpi=dpi)
    try:
        grid = gridspec.GridSpec(2, 3, figure=fig, hspace=0.0, wspace=0.30)

        for column, (title, panels) in enumerate(PANEL_COLUMNS):
            top = fig.add_subplot(grid[0, column])
            bottom = fig.add_subplot(grid[1, column], sharex=top)
            for row, (ax, panel) in enumerate(zip((top, bottom), panels)):
                values = (
                    _ratio_values(fits_by_point, panel)
                    if isinstance(panel, RatioPanel)
                    else _peak_values(fits_by_point, panel)
                )
                _draw_panel(ax, values, positions, panel, is_bottom=(row == 1),
                            rng=np.random.default_rng(42 + column * 2 + row))
            top.set_title(title, fontsize=_FS_TITLE, fontweight="bold", pad=10)

        per_position = spectra / len(positions) if positions else 0
        fig.suptitle(
            f"{sample_name}  {material_name} — Raman quality analysis "
            f"({len(positions)} positions × {per_position:.0f} spectra)",
            fontsize=_FS_SUPTITLE, fontweight="bold", y=1.0,
        )

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        return buf.getvalue()
    finally:
        plt.close(fig)
