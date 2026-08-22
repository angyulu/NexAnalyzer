# NexAnalyzer v3.1.0 - Project Summary

## Overview

NexAnalyzer is Nexstrom's measurement data analyzer: a desktop web application that turns raw
measurement files into fitted results and shareable reports. Built with Streamlit and Python,
it is organized as a platform — a technique-agnostic `core/` plus one module per measurement
technique — with Raman and Photoluminescence (PL) spectra as the first module.

For the feature list, installation steps, and day-to-day usage, see [README.md](../README.md) and [USER_GUIDE.md](../USER_GUIDE.md). For version-by-version history, see [CHANGELOG.md](../CHANGELOG.md). This document covers architecture, data model, and the technical decisions behind them — the things a developer working on the codebase needs that a user-facing doc doesn't cover.

### The one rule

`modules/*` may import `core`; **`core` never imports `modules`**. `core` holds what has no
knowledge of peaks or spectra (report assembly, native dialogs, figure export, page-width
rendering); everything that knows what a peak is lives in `modules/spectra`. Within a tree
imports are relative, across trees absolute. Adding a technique means adding a package under
`modules/` and registering its pages in `app.py` — nothing in `core` changes.

---

## Technical Architecture

### Frontend
- **Framework**: Streamlit (Python web framework for data apps), multi-page via `st.navigation()` (v2.11.0+)
- **Pages**: grouped under a "Raman & PL" section — **Spectra** (`pages/1_Spectra.py`: sidebar + full-width plot, the entire spectrum workflow), **Sample Report** (`pages/2_Sample_Report.py`: generates a three-slide PPTX from a sample folder's 9-point OM + Raman + PL grid), and **Material Presets** (`pages/3_Material_Presets.py`: create/edit/delete materials).
- **State Management**: Streamlit session state with automatic persistence
- **Visualization**: Plotly (interactive multi-layer plots)

### Backend
- **Data Model**: `SpectrumFile` dataclass with `original_data`, `raw_data`, `processed_data` layers
- **Processing Pipeline**:
  1. X-range cropping (modifies `raw_data`)
  2. De-spiking (modifies `processed_data`)
  3. Baseline correction (modifies `processed_data`)
  4. Peak fitting (stores `FitResult`)
- **Algorithms**:
  - **De-spiking**: Modified Z-score spike detection
  - **Baseline**: Polynomial, ALS, Rolling Ball, Spline, airPLS
  - **Fitting**: Voigt profile (lmfit Levenberg-Marquardt)

### Project Structure
```
nexanalyzer/
├── app.py                          # Composition root: page config, module state, routing
├── pages/
│   ├── 1_Spectra.py                # Spectra page: sidebar + full-width plot
│   ├── 2_Sample_Report.py          # Sample Report page: folder -> three-slide PPTX
│   └── 3_Material_Presets.py       # Material Presets page: create/edit/delete materials
├── core/                           # Platform. Knows nothing about peaks or spectra.
│   ├── paths.py                    # PROJECT_ROOT / DATA_DIR, anchored on this file
│   ├── version.py                  # APP_NAME, __version__, REPO_URL (single source of truth)
│   ├── io/
│   │   ├── export.py               # Figure PNG/HTML rasterization, native Save-As dialog,
│   │   │                           # output filename construction
│   │   ├── folder_picker.py        # Native folder-picker dialog (isolated subprocess)
│   │   └── report_settings.py      # Persisted default-material setting
│   ├── report/
│   │   ├── models.py               # SampleScan, PeakStat — the row/scan contracts a module
│   │   │                           # fills in for the report renderer
│   │   ├── pptx.py                 # Three-slide .pptx assembly (OM grid + stats tables +
│   │   │                           # per-point figure grids)
│   │   └── slides.py               # Renders a .pptx's slides to PNG via PowerPoint COM,
│   │                               # in an isolated subprocess
│   └── viz/
│       └── render.py               # Page-width-aware st.plotly_chart wrapper
├── modules/                        # One package per measurement technique
│   └── spectra/                    # Raman & PL
│       ├── models/
│       │   ├── spectrum.py         # SpectrumFile, ProcessingSettings, SpectrumData
│       │   ├── peak.py             # PeakDefinition, FittedPeak, FitResult
│       │   └── preset.py           # MaterialPreset, PeakTemplate, parse_exclusion_ranges
│       ├── processing/
│       │   ├── parser.py           # Two-column .txt file parsing
│       │   ├── despiking.py        # Modified Z-score spike removal
│       │   ├── baseline.py         # 5 baseline algorithms + quality metrics
│       │   ├── fitting.py          # Voigt peak fitting with Levenberg-Marquardt
│       │   ├── auto_workflow.py    # One-click preset-driven pipeline execution
│       │   ├── sample_scanner.py   # Sample-folder discovery by filename pattern
│       │   ├── sample_batch.py     # Per-sample batch-fit orchestration
│       │   └── peak_metrics.py     # Peak height/stderr, raw-spectrum stats, mean/std
│       │                           # aggregation, amplitude ratios (one rule, one place)
│       ├── io/
│       │   ├── preset_store.py     # JSON material-preset storage (data/materials.json)
│       │   └── results_csv.py      # Fit-results CSVs: per-file and master
│       ├── ui/
│       │   ├── sidebar.py          # Material dropdown, the only processing entry point
│       │   │                       # (Run Auto-Workflow / Run All Files), Quick/Batch
│       │   │                       # Export, Reset to Raw, file list, View Options
│       │   ├── session_state.py    # Session state management
│       │   └── sample_report_state.py  # Isolated session-state namespace for Sample Report
│       ├── viz/
│       │   ├── live_plot.py        # Interactive multi-layer plot + file navigation
│       │   └── fit_plot.py         # Static data+fit+components figures for export and the
│       │                           # Sample Report's grids (`show_residuals=False`)
│       └── utils/
│           └── fit_staleness.py    # Preprocessing-hash fingerprinting (stale-fit detection)
├── data/
│   ├── materials.json              # Shared material preset store (committed)
│   └── report_settings.json        # Per-installation preference (gitignored)
├── tests/
│   ├── unit/                       # pytest suite for core/ and modules/
│   └── integration/                # streamlit.testing.v1.AppTest-driven page tests
├── docs/                           # This file + algorithm notes
├── pyproject.toml                  # pytest configuration
└── requirements.txt                # Python dependencies
```

`src/ui/control_panel/` (v2.7.1 layout) was a single ~2,700-line file through v2.7.1; it was
split into a package (one module per accordion section) in v2.8.0, with
`compute_preprocessing_hash()` / `mark_fit_stale_if_needed()` moved to
`modules/spectra/utils/fit_staleness.py` since they have no UI dependency (fixing a
layering violation where the processing-layer `auto_workflow.py` had to
import from the UI layer to reach them). In v2.9.0 the manual per-section
UI (`processing_range.py`, `despike.py`, `baseline.py`, `peak_fit.py`,
`shared.py`) was removed entirely, leaving only `export.py` in the package.
In v2.10.0 the package was retired altogether: its remaining pieces (Quick
Export, Batch Export, View Options, Reset to Raw) moved into `sidebar.py`,
the on-screen plot preview was dropped (the composite figure is still built
internally for PNG/HTML export, just not rendered), and Project save/load
was removed from the UI. In v3.0.0 the orphaned `project_io.py`/`project.py`
modules behind it were deleted too, along with `StylingPreferences` (written
to session state on every launch but never read). See
[CHANGELOG.md](../CHANGELOG.md) for the details.

**v2.11.0**: material presets moved from an Excel file
(`presets/material_presets.xlsx`, parsed by the now-deleted
`src/io/preset_parser.py` (deleted)) to an embedded JSON store
(`data/materials.json`, read/written by `modules/spectra/io/preset_store.py`)
edited through the new Material Presets page. `PresetLibrary` (a wrapper
class whose only job was decoding Excel's `"Material_Mode"` sheet-name
convention back into two fields) was removed in favor of a plain
`dict[(material_name, mode), MaterialPreset]`, since JSON presets already
store those as separate fields — no decode step needed. `PeakTemplate.amplitude`
was also dropped: `modules/spectra/processing/fitting.py` auto-estimates amplitude from
the actual data and never reads the preset's value (this was already
documented on `PeakDefinition.amplitude`), so the field was pure schema
weight carried over from the Excel format. The app also became multi-page
(`app.py` is now just an `st.navigation()` entrypoint) so the new editor
page could exist alongside the original single-page workflow, and View
Options moved to the very bottom of the sidebar. See
[CHANGELOG.md](../CHANGELOG.md) for the full list.

**v2.12.0**: added the **Sample Report** page — the "future page" the
v2.11.0 nav-section grouping was explicitly left room for. Given a sample
folder with a 9-point OM + Raman + PL grid, it fits every Raman/PL file
against one material's presets (`modules/spectra/processing/sample_batch.py`, a thin
per-file loop over the existing `execute_auto_workflow()` — no new fitting
logic) and assembles a three-slide `.pptx` (`core/report/pptx.py`): an
overview slide (OM grid + fit-summary tables, `modules/spectra/processing/peak_metrics.py`),
then a 3x3 grid of each point's fitted spectrum for Raman and for PL, reusing
`plotter.plot_composite()` (now with a `show_residuals` flag, off for the
small grid cells) rather than building a second plotting code path. The
generated `.pptx` is rendered back to PNG for the on-screen preview and for
saved page images (`core/report/slides.py`) via PowerPoint COM automation —
run in an isolated subprocess rather than in-process, since Streamlit executes
page scripts on a worker thread and COM apartments are thread-local (calling
`win32com` directly from the page crashed with an unrecoverable
`RPC_E_DISCONNECTED`, invisible to ordinary `try/except`). See
[CHANGELOG.md](../CHANGELOG.md) for the full list, including the still-open gap
around sample folders whose point files are themselves multi-spectrum
hyperspectral files.

---

## Data Model

### SpectrumFile
```python
@dataclass
class SpectrumFile:
    filename: str                            # Original filename
    mode: Literal["Raman", "PL"]             # Spectroscopy mode
    original_data: SpectrumData              # True original (never modified)
    raw_data: SpectrumData                   # After X-range cropping
    processed_data: SpectrumData             # After despike + baseline
    source_dir: Optional[str] = None         # Folder the file was loaded from (v2.7+)
    processing_settings: ProcessingSettings  # Parameters for all algorithms
    peak_table: list = ...                   # User-defined PeakDefinition list
    fit_result: Optional[FitResult] = None
    auto_detected: bool = False              # Mode auto-detected from filename?
    x_range_enabled: bool = False
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    # Workflow status flags
    despike_done: bool = False
    baseline_done: bool = False
    fit_done: bool = False
    fit_stale: bool = False                  # True if preprocessing changed since last fit
    last_preprocessing_hash: Optional[str] = None
```
See `src/models/spectrum.py` for the authoritative field list and validation rules.

### ProcessingSettings
```python
@dataclass
class ProcessingSettings:
    despike_threshold: float = 30.0
    despike_applied: bool = False
    baseline_algorithm: Literal["Polynomial", "ALS"] = "ALS"
    baseline_degree: int = 3
    baseline_lambda: float = 10000.0
    baseline_p: float = 0.001
    baseline_applied: bool = False
    y_shift: float = 0.0                     # Auto Y-shift applied for baseline stability
```

### FitResult
```python
@dataclass
class FitResult:
    success: bool
    fitted_peaks: list[FittedPeak]
    total_fit_curve: np.ndarray
    residuals: np.ndarray
    chi_squared: float
    r_squared: float
    convergence_time: float
    error_message: str = ""
```

---

## Key Technical Decisions

### 1. Three-Layer Data Model
- **original_data**: Preserves true original before any processing (Issue #5 fix)
- **raw_data**: After X-range cropping (reset point for despike/baseline)
- **processed_data**: After all processing (used for peak fitting)

**Rationale:** Allows "Reset to Raw" to restore the full original dataset, not just the cropped version.

### 2. Mode-Aware Parameter Bounds
- Raman: center tolerance ≥5 cm⁻¹ (or 5% of FWHM, whichever is larger)
- PL: center tolerance ≥30 nm (or 10% of FWHM, whichever is larger)
- Adaptive FWHM bounds: 0.5× to 3× initial guess

**Rationale:** Prevents parameter runaway, improves convergence rate — see [Fitting_Algo.md](Fitting_Algo.md) §8 for measured before/after numbers.

### 3. Selectbox On-Change Callback for Navigation
- Previous approach: button updates state → `st.rerun()` → race condition
- Current approach: button updates state → selectbox callback handles rerun
- No manual `st.rerun()` calls in button handlers

**Rationale:** Fixes a race condition between button handlers and selectbox widget evaluation.

### 4. "None (Skip)" Baseline Option
- Physically accurate for PL emission spectra (the peak IS the signal)
- Avoids fighting baseline algorithms when no real background exists
- Still marks the baseline stage as "done" so the workflow can advance

**Rationale:** When a peak covers most of the spectrum, it violates baseline algorithms' core assumption (peaks = narrow features against a background).

### 5. File-Upload Handlers Must Guard Against Re-Processing
- `st.file_uploader`'s return value stays truthy across reruns until the user removes the file or picks a different one
- A handler that acts on it unconditionally re-runs on every subsequent rerun — at best silently redoing the same work, at worst (if it also calls `st.rerun()`) an infinite rerun loop that prevents the rest of the app from ever rendering
- Fixed (v2.8.0) in the "Load Project" handler by tracking the uploaded file's stable `.file_id` and only processing when it changes

**Rationale:** This is a general Streamlit `file_uploader` gotcha, not specific to project loading — worth knowing before adding another upload-driven feature.

---

## Known Issues & Limitations

1. **No recursive folder scan**: users pick individual files (or multi-select within one dialog session); subtree walking is not supported.
2. **Cloud deployment constraints**: the native tkinter file picker (and the Sample Report page's folder picker and PowerPoint COM automation) only work on local Windows Streamlit installations (not Streamlit Cloud / headless servers / macOS or Linux).
3. **No multi-stage peak fitting**: single-stage Levenberg-Marquardt optimization is still prone to local minima with many closely-spaced peaks — see [Fitting_Algo.md](Fitting_Algo.md) §6.5.
4. **Sample Report doesn't yet support multi-spectrum-per-point sample folders**: some real sample folders have each `Raman_N.txt`/`PL_N.txt` file containing ~100 sub-spectra rather than one; these currently fail to parse per point and are excluded gracefully rather than fit. See CHANGELOG's v2.12.0 entry.

For resolved issues, see [CHANGELOG.md](../CHANGELOG.md).

---

## Testing

A pytest suite lives under `tests/unit/`, covering the pure processing/IO/model
logic: despiking, all 5 baseline algorithms, Voigt fitting, spectrum parsing,
JSON preset storage, CSV/project export and import, and stale-fit detection.
Run with `pytest` from the repo root (configured via
`pyproject.toml`).

`tests/integration/test_sample_report_flow.py` (v2.12.0+) drives the actual
Sample Report page via `streamlit.testing.v1.AppTest` — folder scan through
Generate Report through a built `.pptx` — closing part of the UI-workflow
integration gap below for that one page.

**Not yet covered**:
- End-to-end UI-workflow integration tests for the Analysis page (X-range → Despike → Baseline → Fit → Export)
- A benchmark suite against real Raman/PL spectra with known ground truth
- PowerPoint COM slide rendering (`core/report/slides.py`) — drives a real desktop app, same as the tkinter dialogs

---

## Quick Reference

### File Navigation
- **Dropdown**: Select any file from the loaded list
- **◀ (Previous)**: Navigate to previous file (wraps around)
- **▶ (Next)**: Navigate to next file (wraps around)
- **Counter**: Shows "File X of Y"

### Plot Layer Toggles
- **Raw**: Original data (before any processing)
- **De-spiked**: After spike removal
- **Baseline-Corrected**: After baseline subtraction
- **Fit Total**: Sum of all fitted peaks
- **Peak Components**: Individual peak curves
- **Residuals**: Baseline-corrected data minus Fit Total

### Baseline Algorithms
1. **Polynomial**: Fast, good for smooth backgrounds (Raman)
2. **ALS** (Asymmetric Least Squares): Adaptive asymmetry (Raman/PL)
3. **Rolling Ball**: Local baseline, robust to outliers
4. **Spline**: Smooth interpolation with local control
5. **airPLS**: Adaptive iterative reweighted penalized least squares (best for wide peaks)
6. **None (Skip)**: Skip baseline correction (for ultra-wide PL peaks)

### Peak Shape Parameter
- **0.0**: Pure Gaussian (narrow, symmetric)
- **0.5**: Mixed Voigt (most common for Raman)
- **1.0**: Pure Lorentzian (wide, long tails for PL)

---

## Acknowledgments

- **Streamlit**: Web framework for data apps
- **Plotly**: Interactive visualization library
- **lmfit**: Levenberg-Marquardt optimization
- **NumPy/SciPy**: Scientific computing libraries

---

**Last Updated:** 2026-08-21
**Project Version:** v2.12.0
