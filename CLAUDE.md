# CLAUDE.md

NexAnalyzer — Nexstrom's measurement data analyzer. Streamlit app: raw spectra in,
fitted results and .pptx reports out.

Architecture, data model and the reasoning behind them live in
[docs/Summary.md](docs/Summary.md); version history in
[CHANGELOG.md](CHANGELOG.md). This file holds only what's easy to get wrong.

## Commands

```bash
pytest                  # 456 tests; pythonpath and testpaths come from pyproject.toml
python -m ruff check .   # F + E9 only — deliberately narrow, so a hit is real breakage
streamlit run app.py     # or start.bat, which also creates venv and pulls updates
```

## Two quantities, two names — never "amplitude"

A peak has a maximum and it has an area. These are different numbers, they differ
by a factor of ~FWHM × 1.064, and confusing them has caused real reporting bugs
here (v3.3.0 shipped a .pptx that disagreed with its own CSV).

| Quantity | Our name | lmfit's name |
| --- | --- | --- |
| The fitted curve's maximum | **intensity** | — |
| The area under the peak | **area** | `amplitude` |

- `peak_metrics.peak_intensity()` / `peak_intensity_and_stderr()` is the only way
  to get an intensity. `PeakDefinition.intensity`, `PeakStat.intensity_*`,
  `intensity_max`, and the `Intensity` column all mean the maximum.
- `FittedPeak.area` / `area_stderr` is the integral. It is named `area` precisely
  *because* lmfit calls it `amplitude`.
- **Every reporting surface shows intensity** — the on-screen Fit Results table,
  both CSVs, the Sample Report's tables, and the LA/E2g+A1g and B2g/E2g+A1g
  ratios. They agree, and must keep agreeing.
- The word "amplitude" appears only where lmfit's own parameter is addressed by
  name (`params.add(f"{prefix}amplitude", ...)`). Don't reintroduce it anywhere
  else. Guard tests in
  [tests/unit/test_peak_metrics.py](tests/unit/test_peak_metrics.py) assert that
  `amplitude*` and `height*` stay gone from the models.

The full reasoning is in the
[peak_metrics.py](modules/spectra/processing/peak_metrics.py) module docstring.

## Other invariants

- **`modules/*` may import `core`; `core` never imports `modules`.** See "The one
  rule" in docs/Summary.md.
- **FWHM means the Voigt FWHM.** Use `fitting.voigt_fwhm(sigma, gamma)`. Reporting
  `2.355 * sigma` — the Gaussian half, ignoring the Lorentzian — was a real bug
  fixed in v3.4.0. It under-reports every width.
- **The preset owns position and width; the data owns intensity.** `fit_voigt_peaks()`
  auto-estimates the initial intensity from the spectrum at fit time, because
  intensity depends on measurement conditions while center/FWHM are material
  properties. `PeakDefinition.intensity` is a required-but-unused placeholder.
  The *tolerance* is part of "owns position": carry it on
  `PeakDefinition.center_tolerance`, never by writing `center_min`/`center_max`
  from a caller. `calculate_auto_bounds()` runs on every fit and is the only
  thing that writes those two, so bounds set anywhere else are overwritten with
  the mode default — which is what cost WSe₂ five of its seven tolerances before
  v4.0.0.
- **A preset is keyed by material alone; technique comes from the filename.**
  `MaterialPreset` holds `raman` / `pl` `TechniquePreset` blocks and an
  `optical` dict of `OpticalParams` keyed by layer. Resolve with
  `preset.block_for(spectrum.mode)`; a block may legitimately be absent.
  `data/materials.json` is v2 (an object with `schema_version`); the v1 array is
  migrated on load by a shim in `preset_store`, and
  [tests/unit/test_preset_migration.py](tests/unit/test_preset_migration.py)
  asserts the committed file is already v2 so that shim stays deletable.
- **Optical layers are stored as `"1L"`/`"2L"`, never as the word.**
  `contrast.layer_word()` is one-way presentation and passes unknown values
  through, so keying persisted JSON by its output would orphan every stored
  block the day the wording changed. Render the word, store the code.
- **`OpticalParams` fields default to `None` meaning "contrast.py's default".**
  Keep the numbers in `contrast.py` alone, so a material with no optical block
  runs `analyse_frame(**{})` — which is what keeps
  [tests/unit/test_om_contrast.py](tests/unit/test_om_contrast.py)'s locked
  numbers meaningful. `mask_margin` and `ff_divisor` apply to **both** frame
  types: `is_circular()` decides that per image at runtime, so a preset cannot
  address one of them. `ff_divisor` is a divisor, not a sigma — larger means a
  smaller blur.
- **`core/version.py` is the single source of truth for the version.** Bump it and
  add a CHANGELOG entry in the same change as any user-visible behaviour change;
  note explicitly when numbers don't move (renames) versus when they do.

## Doc trust levels

- [docs/Summary.md](docs/Summary.md) — current.
- [docs/Fitting_Algo.md](docs/Fitting_Algo.md) — §1–§4 verified against the code at
  v3.6.0. §5–§8 are history; their listings quote code as it stood at the time.
- [docs/Baseline_Algo.md](docs/Baseline_Algo.md) — paths repointed at v3.6.0, but the
  algorithm content has not been re-verified since v2.9.0. Check against the code
  before relying on it.
- [docs/OM_Contrast_Algo.md](docs/OM_Contrast_Algo.md) — the spec for
  `modules/optical/processing/contrast.py`, vendored verbatim from the research
  script at v3.10.0. The code was checked against it and against that script's
  own output; keep them in step, and read it before touching the segmentation.
  Its tuning figures are still the defaults, but since v4.0.0 they are
  overridable per material and layer from the preset, and the doc's
  "circular"-labelled rows (σ_ff, margin) are applied to both frame types.
