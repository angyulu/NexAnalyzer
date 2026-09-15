"""
Per-wafer adaptive placement of the absolute contrast threshold pair.

The classifier itself is untouched: frames are still segmented by
`contrast.classify(abs_threshold=(below, above))`, the operator-validated
path. What this module adds is where that pair comes from. A material preset
stores one fixed pair calibrated for the whole material (`WSe2-HA` carries
-6.0/+4.25), but wafers differ: the trilayer valley that sits at +4 % on one
wafer sits at +2.5 % on another, and a pair tuned for the material average
undercounts the wafer that drifted. HADH51 (202609) is the worked example:
at +4.25 % it reports 2.0 % "Above 2L"; its own pooled histogram puts the
boundary at +2.46 %, which reports 10.8 % -- and +2.46 is within 0.04 of the
+2.5 the operator found by hand in that wafer's threshold sweep.

How the pair is derived, per wafer:

1. Pool green contrast (percent of each frame's own mode) across all frames.
   Pooling nine frames stabilizes the histogram enough to fit; single frames
   are too noisy to move a threshold on.
2. Fit a five-component Gaussian mixture seeded at k * 5 % -- the layer-step
   contrast on this substrate -- with each mean confined to its seed +/- 2 %.
   The physics prior is the point: populations live near layer steps, so a
   component that wanders to the window edge nearest the film is fitting the
   film's tail, not a population, and is ignored.
3. A side's cut moves off the preset pair only on strong evidence:
   an empirical valley in the pooled density (preferred -- it is what the
   operator's threshold sweep finds by eye), else the posterior crossing
   against a population that is compact (sigma <= 1.5x the film's) and
   substantial (>= 3 % weight). Anything weaker keeps the preset cut.
4. Guardrails, in the order they bite:
   - a cut never sits closer to the mode than GATE_RATIO x the robust noise
     sigma. Noise is estimated from the MAD of lag-4 pixel differences, which
     domain content cannot inflate -- the failure mode that motivated the
     fixed pair in the first place (see classify()'s docstring);
   - a population whose Bhattacharyya overlap with the film exceeds 65 %
     (under ~2 sigma separation) cannot be thresholded at any value: the side
     keeps the preset cut and says why;
   - when even the preset cut fails the noise gate, the side is NOT
     MEASURABLE: every percentage it produces is segmentation noise and the
     wafer needs re-imaging, not retuning. This is the summary CSV's
     threshold-to-sigma rule, applied before the numbers are produced
     instead of after.

Validated 2026-09-15 against the HA 202609 set (52 wafers): 21 moved a cut,
30 kept the preset pair byte-for-byte, 7 flagged not measurable -- a superset
of the QC summary's re-image list. HADG38 (below-rich control) and HADH26
(textured film) reproduce the fixed pair's numbers exactly.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi

from . import contrast

# Layer-step contrast on SiO2/Si, percent per step. The mixture seeds and the
# mean windows both come from it; docs/OM_Contrast_Algo.md carries the physics.
DELTA = 5.0
SEEDS = np.array([-2.0, -1.0, 0.0, 1.0, 2.0]) * DELTA
MEAN_WINDOW = 2.0
SIGMA_CAP = 0.9 * DELTA
WEIGHT_PRUNE = 0.003
#: Bhattacharyya overlap above which a population cannot be cut from the film.
BC_MERGE = 0.65
#: Mixture weight below which a population is too small to move a cut for.
MIN_POPULATION_W = 0.03
#: A cut must clear this many robust-noise sigmas, and a side whose final cut
#: does not is not measurable. 2.0 sigma is the QC summary's own usability rule.
GATE_RATIO = 2.0
CUT_BOUNDS = {"below": (2.5, 10.0), "above": (2.0, 8.0)}
POOL_PER_FRAME = 80_000
NOISE_LAG = 4


def robust_noise_sigma(g: np.ndarray, valid: np.ndarray, lag: int = NOISE_LAG) -> float:
    """Noise sigma from the MAD of lag-`lag` pixel differences, both axes.

    Layer domains are piecewise constant, so a step contributes only to the
    minority of pixel pairs that straddle a boundary and the median ignores
    them. This is what makes the estimate immune to the feedback trap that
    histogram half-widths suffer (classify()'s docstring): domain content
    cannot move it, however pervasive.
    """
    estimates = []
    for axis in (0, 1):
        diff = g - np.roll(g, lag, axis=axis)
        pair_valid = valid & np.roll(valid, lag, axis=axis)
        window = [slice(None)] * 2
        window[axis] = slice(lag, None)
        vals = diff[tuple(window)][pair_valid[tuple(window)]]
        mad = np.median(np.abs(vals - np.median(vals)))
        estimates.append(mad * 1.4826 / np.sqrt(2))  # difference of two iid
    return float(np.mean(estimates))


def _em_fit(x: np.ndarray, sigma0: float):
    """Physics-seeded mixture fit in contrast space. `sigma0` in percent."""
    mu = SEEDS.copy()
    sg = np.full(5, max(sigma0, 0.4))
    w = np.array([0.02, 0.08, 0.80, 0.08, 0.02])
    for _ in range(100):
        p = np.stack([
            wk / max(sk, 1e-6) * np.exp(-0.5 * ((x - m) / max(sk, 1e-6)) ** 2)
            for wk, m, sk in zip(w, mu, sg)
        ])
        p /= np.maximum(p.sum(0), 1e-300)
        nk = p.sum(1)
        w = nk / x.size
        mu = np.clip((p * x).sum(1) / np.maximum(nk, 1e-9),
                     SEEDS - MEAN_WINDOW, SEEDS + MEAN_WINDOW)
        sg = np.sqrt((p * (x - mu[:, None]) ** 2).sum(1) / np.maximum(nk, 1e-9))
        sg = np.clip(sg, 0.5 * max(sigma0, 0.3), SIGMA_CAP)
    w[w < WEIGHT_PRUNE] = 0.0
    return mu, sg, w


def _bhattacharyya(m1, s1, m2, s2) -> float:
    db = (m1 - m2) ** 2 / (4 * (s1 ** 2 + s2 ** 2)) + \
        0.5 * np.log((s1 ** 2 + s2 ** 2) / (2 * s1 * s2))
    return float(np.exp(-db))


def _crossing(w1, m1, s1, w2, m2, s2) -> float:
    """x between the means where the two weighted gaussians are equal."""
    a = 1 / (2 * s2 ** 2) - 1 / (2 * s1 ** 2)
    b = m1 / s1 ** 2 - m2 / s2 ** 2
    c = m2 ** 2 / (2 * s2 ** 2) - m1 ** 2 / (2 * s1 ** 2) + \
        np.log((w1 * s2) / (w2 * s1))
    lo, hi = min(m1, m2), max(m1, m2)
    if abs(a) < 1e-12:
        roots = [-c / b] if abs(b) > 1e-12 else []
    else:
        disc = b ** 2 - 4 * a * c
        roots = [] if disc < 0 else [(-b + s * np.sqrt(disc)) / (2 * a)
                                     for s in (1, -1)]
    inside = [r for r in roots if lo < r < hi]
    return float(inside[0]) if inside else (m1 + m2) / 2


def _find_valley(pool, mu_ref, sig_ref, mu_dom) -> Optional[float]:
    """Empirical dip of the pooled density between the film flank and the
    population center; None when the density is monotone there. Direct
    evidence, so it outranks anything the parametric fit says."""
    hist, edges = np.histogram(pool, bins=240, range=(-18, 12), density=True)
    dens = ndi.gaussian_filter1d(hist, 2.0)
    ctr = (edges[:-1] + edges[1:]) / 2
    start = mu_ref + np.sign(mu_dom - mu_ref) * 1.5 * sig_ref
    lo, hi = sorted((start, mu_dom))
    win = np.where((ctr >= lo) & (ctr <= hi))[0]
    if win.size < 5:
        return None
    i = win[np.argmin(dens[win])]
    if i in (win[0], win[-1]):                       # monotone: no valley
        return None
    ref_edge = dens[win[0]] if mu_dom < mu_ref else dens[win[-1]]
    dom_peak = dens[win[-1]] if mu_dom < mu_ref else dens[win[0]]
    dom_peak = max(dom_peak, np.interp(mu_dom, ctr, dens))
    if dens[i] > 0.8 * min(ref_edge, dom_peak):      # dip too shallow
        return None
    return float(ctr[i])


@dataclass(frozen=True)
class AdaptivePair:
    """One wafer's derived threshold pair, with its provenance.

    `pair` plugs straight into `analyse_frame(abs_threshold=...)`. The rest is
    what a reviewer needs to trust or overrule it: where each cut came from
    (`valley` / `crossing` moved it; anything starting with `default` kept the
    preset value, and says why; `NOT MEASURABLE` means even the preset cut sits
    inside the frame noise), and each cut's distance from the mode in robust
    noise sigmas.
    """

    pair: Tuple[float, float]
    base: Tuple[float, float]
    below_source: str
    above_source: str
    below_gate: float
    above_gate: float
    below_measurable: bool
    above_measurable: bool
    noise_sigma_pct: float

    @property
    def moved(self) -> bool:
        return self.below_source in ("valley", "crossing") or \
            self.above_source in ("valley", "crossing")

    @property
    def flags(self) -> List[str]:
        out = []
        if not self.below_measurable:
            out.append("below NOT MEASURABLE")
        if not self.above_measurable:
            out.append("above NOT MEASURABLE")
        return out

    def describe(self) -> str:
        """One line for a status box or a log."""
        text = (f"adaptive pair -{self.pair[0]:.2f}/+{self.pair[1]:.2f} % "
                f"(below: {self.below_source}, {self.below_gate:.1f} sigma; "
                f"above: {self.above_source}, {self.above_gate:.1f} sigma; "
                f"base -{self.base[0]:.2f}/+{self.base[1]:.2f})")
        if self.flags:
            text += "  ** " + "; ".join(self.flags) + " **"
        return text


def _place_side(side: str, pool, mu, sg, w, noise_sigma: float,
                base: Tuple[float, float]):
    """One side's cut. Returns (cut, source, gate, measurable)."""
    candidates = (1, 0) if side == "below" else (3, 4)   # nearest step first
    default = base[0] if side == "below" else base[1]
    lo_bound, hi_bound = CUT_BOUNDS[side]
    floor = GATE_RATIO * noise_sigma

    def finish(cut, source):
        cut = float(np.clip(cut, lo_bound, hi_bound))
        if cut / max(noise_sigma, 1e-6) < GATE_RATIO:    # adaptive cut in noise
            cut, source = float(np.clip(default, lo_bound, hi_bound)), "default"
        gate = cut / max(noise_sigma, 1e-6)
        measurable = gate >= GATE_RATIO
        if not measurable:
            source = "NOT MEASURABLE"
        return cut, source, gate, measurable

    for k in candidates:
        if w[k] <= 0:
            continue
        inner = SEEDS[k] + MEAN_WINDOW if k < 2 else SEEDS[k] - MEAN_WINDOW
        if abs(mu[k] - inner) < 0.05:        # pinned toward the film: tail-fit
            continue
        bc = _bhattacharyya(mu[2], sg[2], mu[k], sg[k])
        if bc > BC_MERGE:
            if w[k] > MIN_POPULATION_W:      # real mass, unresolvable
                return finish(default, f"default (unresolved pop near {mu[k]:+.1f}%)")
            continue
        valley = _find_valley(pool, mu[2], sg[2], mu[k])
        if valley is not None:
            return finish(max(abs(valley - mu[2]), floor), "valley")
        if w[k] < MIN_POPULATION_W:          # too little mass to act on
            continue
        if sg[k] > 1.5 * sg[2]:              # broad smear: boundary unlocatable
            return finish(default, f"default (broad shoulder near {mu[k]:+.1f}%)")
        cut = abs(_crossing(w[2], mu[2], sg[2], w[k], mu[k], sg[k]) - mu[2])
        return finish(max(cut, floor), "crossing")
    return finish(default, "default")        # no population: keep the preset


def derive_pair_from_pool(pool: np.ndarray, noise_sigma_pct: float,
                          base: Tuple[float, float]) -> AdaptivePair:
    """Derive the pair from an already-pooled contrast sample.

    `pool` is green contrast in percent of the film mode, pooled across the
    wafer's frames; `noise_sigma_pct` the robust noise sigma in the same
    units. Pure and deterministic, which is what the unit tests exercise.
    """
    mu, sg, w = _em_fit(pool, noise_sigma_pct)
    below, b_src, b_gate, b_ok = _place_side("below", pool, mu, sg, w,
                                             noise_sigma_pct, base)
    above, a_src, a_gate, a_ok = _place_side("above", pool, mu, sg, w,
                                             noise_sigma_pct, base)
    return AdaptivePair(pair=(below, above), base=tuple(base),
                        below_source=b_src, above_source=a_src,
                        below_gate=b_gate, above_gate=a_gate,
                        below_measurable=b_ok, above_measurable=a_ok,
                        noise_sigma_pct=noise_sigma_pct)


def derive_pair(paths: Sequence, base: Tuple[float, float],
                margin: Optional[float] = None,
                ff_divisor: Optional[float] = None) -> AdaptivePair:
    """Derive one wafer's pair from its frame files.

    Frames are prepared exactly as `analyse` prepares them (same mask, same
    flat-field, same smoothing), with the same `margin` / `ff_divisor`
    overrides the preset would pass, so the pool describes the pixels the
    classifier will actually see. Contrast is taken per frame against that
    frame's own mode, which is what lets frames pool across exposure drift.
    """
    rng = np.random.default_rng(0)           # deterministic subsample
    pools, sigmas = [], []
    for path in paths:
        a = contrast.load(path)
        aperture, valid, ftype = contrast.make_mask(a, margin)
        flat = contrast.flatfield(a, aperture, ftype, ff_divisor)
        g = ndi.gaussian_filter(
            flat, sigma=(contrast.SMOOTH_SIGMA, contrast.SMOOTH_SIGMA, 0),
            mode="nearest",
        )[..., 1]
        mode = contrast.histogram_stats(g[valid])["mode"]
        x = (g[valid] / mode - 1.0) * 100.0
        x = x[np.abs(x) < 25]
        if x.size > POOL_PER_FRAME:
            x = rng.choice(x, POOL_PER_FRAME, replace=False)
        pools.append(x)
        sigmas.append(robust_noise_sigma(g, valid) / mode * 100.0)
    return derive_pair_from_pool(np.concatenate(pools), float(np.median(sigmas)),
                                 base)
