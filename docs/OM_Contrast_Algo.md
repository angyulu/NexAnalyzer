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
