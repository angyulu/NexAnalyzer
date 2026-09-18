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
The values are per material. As of v5.0.0 the committed `WSe2` preset carries
the (−6.0, +4.25) pair: the separate `WSe2-HA` entry it came from was folded
into `WSe2`, so fixed contrast is now the default for WSe2 work rather than an
alternative to it. A material that wants the adaptive rule simply omits the
pair.

---

## Divergence from this spec: midpoint thresholds (NexAnalyzer v4.6.0)

`contrast.classify()` accepts a third `threshold_mode`, `"midpoint"`, beside
the adaptive rule this spec describes and v4.4.0's `"absolute"`. Unset, the
code behaves as before: an `abs_threshold` pair selects absolute, nothing
selects adaptive. An explicit mode wins over the pair.

**The rule.** On each side independently: take the pixels beyond the adaptive
cut (`mode ± N·σ_noise`), despeckle them, and measure the mean green of their
interior (eroded 1 px, as `interior_mean` does). That plateau, relative to the
mode, is the layer step `ΔC` for that side, in the sample's own frame. The cut
is placed at `mode ± ΔC/2` — the Bayes boundary between two populations of
equal noise, and 1-D k-means with the reference class pinned to the mode. The
step is *measured*, so a 1L reference, a different oxide or the asymmetry
between one step up and several steps down need no per-material number.

**One pass, deliberately.** Iterating (re-measure at the new cut, move again)
was tried on HADH37 and rejected: each tighter cut admits more of the film's
own tail, the "plateau" drifts toward the cut, and the fixed point sits inside
the film's shoulder (Above 2L 2.2 % → 7.4 % on P1, a frame with visibly few
bright domains). Measured once, beyond `N·σ`, the plateau is the domain interior;
for a resolvable population the truncation bias is under 0.05 σ.

**Two outcomes that are not a midpoint, and how they are shown.**

| status | condition | cut used | coverage means |
| --- | --- | --- | --- |
| `empty` | < 0.1 % of the valid area beyond the adaptive cut | adaptive | ~0, correctly |
| `noise-limited` | `ΔC/2 < 2.5 σ_noise` | adaptive | a **lower bound** |
| `midpoint` | otherwise | `mode ± ΔC/2` | a measurement |

A noise-limited side is printed with `≥` on the figure panel, named in the
histogram box, counted in the figure title, and counted per class in the stats
CSV's `N_Noise_Limited`; the points CSV carries `Threshold_Mode`, `Step_*_pct`
and `Status_*` per frame. This is the "validity gate" paragraph above, made
automatic.

**Why 2.5 σ.** With `N = 4`, a population entirely inside the cut — or no
population at all — leaves a truncated tail beyond it whose mean sits 0.3–0.5 σ
past the cut, so its half-step measures 2.15–2.25 σ. The gate sits just above
what nothing-there produces: it detects "there is a plateau beyond the cut"
rather than tuning a sensitivity. At the gate itself, about 0.6 % of the film's
Gaussian pixels would fall on the wrong side before despeckling — a ~20 % error
on a 3 % class, the most that is worth printing as a number.

**Worked numbers, HADH37 (50x, 2L reference, `N = 4`, `minpx = 3`).**

| frame | σ_noise / mode | ΔC below | ΔC above | cuts (midpoint) | Above 2L, adaptive → midpoint |
| --- | --- | --- | --- | --- | --- |
| P1 | 0.93 % | 9.1 % | 6.3 % | −4.5 % / +3.15 % | 2.2 % → 3.6 % |
| P7 | 1.25 % | 10.9 % | 7.5 % | −5.5 % / +3.74 % | 0.4 % → 1.3 % |

P7 is the case §"absolute thresholds" describes: widened noise pushed the
adaptive cut to +5.0 %, past most of a ~7 % step, and hid two-thirds of the
population. HADG37 (100x, σ_noise 16–41 % of the mode) is the other end: every
side reads `empty`, the adaptive cut stands, and Bilayer stays at 99.96 %
where the fixed pair reports 52 %.

**Known limit.** Two populations on one side (1L and bare substrate under a
2L film) are not separated: the plateau is their area-weighted mean and the
cut lands at half of that, which can split the nearer one. The histogram row
shows it, as it does for the 3L/4L case in "Known limits" above.
