# CLAUDE.md

NexAnalyzer — Nexstrom's measurement data analyzer. Streamlit app: raw spectra in,
fitted results and .pptx reports out.

Architecture, data model and the reasoning behind them live in
[docs/Summary.md](docs/Summary.md); version history in
[CHANGELOG.md](CHANGELOG.md). This file holds only what's easy to get wrong.

## Commands

```bash
pytest                  # 213 tests; pythonpath and testpaths come from pyproject.toml
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
