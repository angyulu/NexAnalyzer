# TMD Optical-Contrast Layer Classification — Algorithm

Validated on ~70 WSe₂ / SiO₂(285 nm) / Si frames at 100×, Sept 2026.
Physics on this substrate: **thicker = brighter** (2L→3L ≈ +5–7 % in G,
substrate ≈ −4 to −10 %). The algorithm never assigns the reference layer
count itself — the user states it (1L or 2L); the algorithm finds
*brighter-than-reference* and *darker-than-reference* populations.

---

## 0. Load
Downscale so max(H, W) ≤ 1400 px (LANCZOS). Work in float RGB.

## 1. Frame-type detection
```
lum      = 0.299 R + 0.587 G + 0.114 B
c        = 3 % of min(H, W)
corners  = median of lum in the four c×c extreme-corner boxes
centre   = median of lum in the central third
circular = corners / centre < 0.5        (typ. ≈0.2 circular, ≈0.9 rectangular)
```
The corner box must be small. A 1/8-frame box straddles the aperture edge
and returns ≈0.85 for both types.

## 2. Mask
| | aperture | valid |
|---|---|---|
| rectangular | whole frame | frame minus **5 %** margin each side |
| circular | `lum > 0.5·centre`, fill holes, open ×3 | aperture eroded by **10 %** of min(H,W) |

Circular needs 10 %: the illuminated disc has a bright ring just inside the
dark border that flat-field cannot remove, and the darkening just inside that
is misread as substrate. 5 % leaves both artifacts in.

## 3. Flat-field (per channel)
```
σ_ff = max(H,W)/8   (rectangular)      σ_ff = max(H,W)/12   (circular)
plane = channel copy
if circular: plane[~aperture] = median(plane[aperture])      # fill black BEFORE blur
bg    = gaussian(plane, σ_ff)
out   = channel / max(bg,1) · mean(bg[aperture])
```
The corner fill stops the black region dragging the background estimate
down near the edge (which manufactures a bright ring). The tighter σ tracks
the steeper vignetting gradient of a circular aperture.

## 4. Smooth
Gaussian σ = 1.0 px on the classifier copy only. Display stays sharp.

## 5. Histogram (green channel, valid pixels only)
300 bins over [min, max], smoothed σ = 3 bins.
```
mode      = argmax
half-max  = 0.5 · peak
HWHM_L    = mode − first bin left  of mode below half-max
HWHM_R    = first bin right of mode below half-max − mode
σ_L, σ_R  = HWHM / 1.177
```

## 6. Noise σ — the key step
```
σ_noise = min(σ_L, σ_R)
```
Whichever side carries a domain population (3L on the right, substrate on
the left) grows a shoulder that inflates *its own* HWHM. Using each side's
own σ therefore pushes the threshold away from the domains and undercounts
them (11002: σ_R = 1.9·σ_L → 1.2 % 3L; min-side → 13.5 %, matching the
visible speckle). The narrower side is the uncontaminated noise width.
Report σ_L, σ_R and flag `max/min > 1.3` so the operator can see it acting.

## 7. Threshold
```
N       = 4                      (3 overcounts on these ~1–2 grey-level widths)
brighter (next layer)   : G > mode + N·σ_noise
darker   (substrate)    : G < mode − N·σ_noise
```
Restricted to `valid`. Despeckle: drop connected components < 3 px.
Reference (2L) = valid − brighter − darker.

## 8. Measure
For each class, erode mask 1 px (exclude boundary-mixed pixels; fall back to
un-eroded if < 30 px remain), then
```
mean R,G,B ;  C_ch = (I_ch − I_ref) / I_ref · 100 % ;  R−B
area % of valid ;  connected-component count
```

## 9. Output
Per image: raw | enhanced ×3 | labelled overlay (red = substrate, green =
next layer, dimmed = excluded) | green histogram with mode and both
thresholds. Batch: CSV of the table above; list frames with reference
coverage > 95 %.

---

## Tunables and when to move them
| parameter | default | move when |
|---|---|---|
| N (σ multiplier) | 4 | 5 if operator reports over-count; 3 if faint domains are missed |
| circular margin | 10 % | 12–15 % if red/green still appears at the aperture edge |
| σ_ff circular | /12 | /16 if vignetting still visible in enhanced view |
| despeckle | 3 px | raise for very noisy cameras |

## Known limits
- Cannot tell 1L from 2L reference — the operator must state it.
- Two brighter populations (3L and 4L) are not separated; would need a
  within-class valley search.
- A frame that is > ~40 % domains has no clean side; min-side still helps
  but N should be checked against the enhanced view.

---

## Divergence from this spec: absolute thresholds (NexAnalyzer v4.4.0)

Everything above describes thresholding at `mode ± N · min(σ_L, σ_R)`, and the
code still does exactly that by default. `contrast.classify()` additionally
accepts `abs_threshold`, which replaces that rule with a fixed green contrast
in percent of the film mode. This section documents the departure; the rest of
the spec is unchanged and still governs every other step.

**Why.** Taking the minimum of the two half-widths defends against *one*
contaminated side — a domain population grows a shoulder that inflates its own
half-width, so the narrower side is the honest noise estimate. The defence
fails when domains are small and pervasive rather than few and large, because
then both halves widen together. `min()` of two equally-inflated numbers is not
a noise width. The threshold rises with the domain content that should be
lowering it, and the population conceals itself.

HADH51 (HA tool, 202609) is the worked case: `σ_L` and `σ_R` agree to twelve
decimal places on frames 1, 3 and 9; 4σ places the "Above 2L" cut at +7.1 %
green contrast against a layer step of ~5 %; 0.14 % of a trilayer-bearing film
is reported as Above 2L, and the 8.95 % contrast of what does survive — well
above one step — shows only the extreme tail is getting through.

**The pair is asymmetric.** 2L→3L is one layer step up; 2L→substrate can be two
or more steps down. Across the HA 202609 set the natural valleys sit near −6 %
and the upper boundary near +4 %, so a symmetric cut puts the low threshold
inside the film's own noise and inflates the Below class.

**Validity gate — read this before trusting a coverage number.** A fixed
contrast only means something when it clears the frame noise. Compute
`abs_threshold / (σ_noise / mode)`; below about 2 the cut is inside the
reference distribution and the class percentages are segmentation noise, not
layer coverage. Of 47 HA 202609 samples, 8 sit at 0.5–1.3 (noise σ of 3.2–8.1 %
of the green mode) and 3 more at 1.8–1.9. Those frames are unmeasurable at any
threshold — under `nsigma` they read ~0 % trilayer, under a fixed contrast
8–31 % — and need re-imaging rather than retuning.

**Which to use.** `nsigma` remains right wherever the histogram has a genuine
valley between populations, which is most well-exposed frames; TSM260803 is the
reference for that case and a fixed +4.25 % measurably degrades it (Above 2L
3.60 % → 1.66 %, class contrast +5.44 % → +7.17 %). Reach for `abs_threshold`
only where the film is unimodal and its own texture has widened both halves.
The values are per material: `WSe2` keeps `nsigma`, `WSe2-HA` carries the
(−6.0, +4.25) pair.

---

## Second divergence: adaptive per-wafer pair (NexAnalyzer v4.5.0-v5.4.0, retired)

> **History. Not how the code works today.** v5.5.0 removed this and
> went back to the preset's fixed pair for every wafer. Of the 42 cuts
> the `crossing` rule placed on the HA 202609 set, 28 landed on the
> 2 sigma floor exactly -- a non-detection recorded as a boundary --
> and HADH57's stored pair could not be re-derived from its own
> frames. Coverage is a comparison, wafer against spec and wafer
> against wafer, so it needs one ruler. The observation that motivated
> the method still stands: on HADH51 the fixed +4.25 % cut does
> undercount 3L. That is now a known, uniform bias rather than a
> per-wafer correction that fired wrongly two times in three.
> See the v5.5.0 CHANGELOG entry.

`abs_threshold` fixed one pair per material; wafers drift. HADH51's trilayer
valley sits at +2.5 % where the material pair says +4.25, and at +4.25 the
population reports 2.0 % instead of ~11 %. The adaptive method
(`modules/optical/processing/adaptive.py`) derives the pair per wafer from its
pooled frames and hands the classifier a concrete abs pair -- everything in
this spec is otherwise unchanged. Since v4.6.0 it is the *default* whenever a
preset sets the abs pair; `adaptive_threshold: false` opts a preset out and
pins the fixed pair (v4.5.0 shipped it opt-in as `adaptive_threshold: true`,
which still loads).

Placement, per side: empirical valley of the pooled density if one exists,
else the posterior crossing against a physics-seeded mixture population that
is compact (sigma <= 1.5x the film's) and substantial (>= 3 % weight); weaker
evidence keeps the preset pair. Guardrails: a cut never sits closer than
2 sigma_robust to the mode (sigma_robust = MAD of lag-4 pixel differences,
which domain content cannot inflate -- the same trap section 6 defends
against, closed at the source); a population overlapping the film by more
than 65 % Bhattacharyya cannot be cut at any value and keeps the preset cut
with a note; a side whose base cut fails the 2 sigma gate is NOT MEASURABLE
and the wafer needs re-imaging, not retuning.

Validated 2026-09-15 on HA 202609 (52 wafers): 21 moved, 30 identical to the
fixed pair, 7 not measurable (superset of the QC re-image list). Where the
fixed pair was already right (TSM-like frames, HADG38, HADH26) the adaptive
result is byte-identical, because "no evidence" keeps the base pair.
