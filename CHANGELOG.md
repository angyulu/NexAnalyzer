# Changelog

All notable changes to NexAnalyzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-08-21

Renamed to **NexAnalyzer** and restructured from a single-purpose spectrum fitter into a
platform: a technique-agnostic `core/` plus one module per measurement technique, with today's
Raman/PL code as the first module (`modules/spectra/`). No analysis behavior changed — same
pipeline, same fit results, same report layout.

### Changed
- **Renamed to NexAnalyzer** (`core/version.py` is now the single source of truth for name and
  version; the UI, launchers, and export filenames read from it instead of hardcoding a string
  in five places).
- **App promoted to the repo root.** `SpectralFit/app.py` is now `app.py`, so a clone is
  `git clone && cd nexanalyzer && start.bat` with no nested folder. The launchers' auto-update
  step no longer reaches one directory up for `.git`.
- **`src/` split into `core/` + `modules/spectra/`** along one rule: `core` knows nothing about
  peaks or spectra, and never imports `modules`. Platform pieces that were filed as
  spectroscopy code moved to `core/` — the PPTX builder (`core/report/pptx.py`), slide
  rasterization (`core/report/slides.py`), native dialogs and figure export (`core/io/`),
  width-aware plot rendering (`core/viz/render.py`).
- **Clearer module names**: `visualization/plotter.py` → `modules/spectra/viz/fit_plot.py`
  (static figures for export/reports), `visualization/unified_plot.py` →
  `modules/spectra/viz/live_plot.py` (the interactive session-state plot),
  `processing/peak_stats.py` → `processing/peak_metrics.py`.
- **Runtime data moved out of the package tree** to `data/` — `materials.json` is committed and
  shared, `report_settings.json` is per-installation and gitignored. Paths resolve through
  `core/paths.py` instead of counting `parent.parent` hops.
- **Pages renamed and reordered** for navigation: Spectra, Sample Report, Material Presets.
- **Sample Report**: the LA/E2g+A1g amplitude ratio is now a bolded final row of the Raman
  fit-summary table instead of a separate text line below it, and the per-point fitted-spectrum
  grids no longer include the residuals strip (unreadable at grid-cell size, and it stole
  height from the spectrum). `plot_composite()` gained `show_residuals`.
- Added `LICENSE` (proprietary, Nexstrom internal) and a root `.gitignore` covering caches,
  local Claude settings, and per-installation data.

### Removed
- **Project save/load** (`src/io/project_io.py`, `src/models/project.py`, 430 lines with tests).
  Its UI was removed in v2.11.0 and never replaced, leaving the module unreachable.
- **`StylingPreferences`** — written into session state on every launch, never read by any plot
  code, along with `get_styling()`/`update_styling()`/`get_mode()`.
- **`add_x_range_indicators()`** and `plot_composite()`'s `x_range_enabled`/`x_min`/`x_max`
  parameters. Unreachable since v2.2: `execute_auto_workflow()` crops the arrays and then resets
  `x_range_enabled` to False, so the branch could never fire. Also dropped the unused
  `width_preset` parameter.
- Orphaned helpers with no call sites: `estimate_peak_bounds()` (a wrapper around
  `PeakDefinition.calculate_auto_bounds()`), `export_single_spectrum_csv()`,
  `detect_negative_x()`, `estimate_baseline_degree()`, and eight unused imports.

### Fixed
- **One rule, one place.** Peak height (`max` of the component curve, with its stderr rescaled
  from lmfit's integrated amplitude) was implemented three times — in the master CSV, in the
  sidebar's Quick Export, and in the on-screen Fit Results table. The PL "Raw row" measurement
  was implemented twice. Both now live in `modules/spectra/processing/peak_metrics.py`
  (`peak_height_and_stderr()`, `raw_peak_stats()`) and are covered by tests; CSV output is
  unchanged.
- Fit-results CSV building moved out of the UI into `modules/spectra/io/results_csv.py`, so
  `sidebar.py` no longer assembles DataFrames inline.
- `_WIDTH_MAP` had lost its only definition when a neighbouring dead function was removed;
  `render_plot()` now lives with it in `core/viz/render.py`.

### Known limitations
- Sample folders where each point file is itself a multi-spectrum hyperspectral file aren't
  fitted yet — carried over from v2.12.0, unchanged.
- The Sample Report's summary tables and its LA/E2g+A1g ratio report lmfit's *integrated*
  amplitude, while the CSVs and the on-screen table report peak *height*. Both conventions are
  now documented in `peak_metrics.py`, but they are still different numbers under the same
  "Amplitude" label.

## [2.12.0] - 2026-08-21

### Added
- **Sample Report page** (`pages/sample_report.py`): pick a sample folder containing a 9-point OM + Raman + PL measurement grid, fit every Raman/PL file against one material's presets, and generate a three-slide PPTX report — no manual plotting or copy-pasting required.
  - **Slide 1 (overview)**: 3x3 OM image grid (magnification selectable, e.g. `100x`/`10x`) plus Raman and PL fit-summary tables (mean ± std of center/amplitude/FWHM per peak label, across the 9 points). For WSe2 Raman specifically, the Raman table carries an extra bolded row with the LA/E2g+A1g amplitude ratio (`compute_peak_amplitude_ratio()` in `src/processing/peak_stats.py`) — omitted automatically for materials without both peak labels.
  - **Slides 2 & 3**: a 3x3 grid of each point's individually fitted spectrum for Raman and PL respectively, rendered with `plot_composite(show_residuals=False)` — the same data+fit+components view used elsewhere in the app, minus the residuals strip, which is unreadable at grid-cell size and only steals height from the spectrum.
  - Missing content (no image, no fit, no stats — e.g. a technique entirely absent from a sample) renders as an empty black-outlined box rather than an error or a gray "N/A" placeholder, keeping partial reports clean.
  - After generating, the page renders the actual .pptx's slides to on-screen preview images (not a separate approximation of the layout) via PowerPoint COM automation (`src/io/slide_render.py`), and saves them alongside the .pptx as `_page1.png`/`_page2.png`/`_page3.png` when you save.
  - Folder discovery (`src/processing/sample_scanner.py`) matches `RM`/`Raman`/`rm`/`raman` (Raman) and `PL`/`pl` prefixes with either `-` or `_` before the point number (e.g. `RM_1.txt`, `RM-8.txt`, `rm-9.txt` all resolve); files that don't match a recognizable pattern are listed as ignored rather than guessed at. A "default material" selection persists across restarts (`src/presets/report_settings.json`, separate from `materials.json`).
  - New dependencies: `python-pptx`, `Pillow`, and (Windows-only, via a `sys_platform` marker) `pywin32` for the PowerPoint COM automation.
- New `tests/integration/test_sample_report_flow.py` drives the actual page via `streamlit.testing.v1.AppTest`, closing the coverage gap Summary.md previously flagged as "not practically unit-testable" for UI-workflow integration.

### Known limitations
- Sample folders where each point file is itself a multi-spectrum hyperspectral file (e.g. ~100 sub-acquisitions per grid point, seen in some real customer QC data) aren't fitted yet — those files currently fail to parse per point and are excluded gracefully (shown in an errors panel) rather than averaged or fit individually. Deferred; `parse_spectrum_multi()` in `src/processing/parser.py` is the building block for when this is picked back up.

## [2.11.0] - 2026-08-12

### Added
- **Multi-page app.** `app.py` is now a thin `st.navigation()` entrypoint grouping pages under a "Spectral Fit" section: **Analysis** (`pages/analysis.py`, today's workflow — unchanged in behavior, just relocated out of `app.py`'s top level) and **Material Presets** (`pages/material_presets.py`, new). Grouping under an explicit section means a future page (e.g. an OM Analyzer) can be added as its own sibling section without reworking these two.
- **Material Presets page**: a full in-app editor (create/edit/delete) for the materials used by Run Auto-Workflow / Run All Files — despike threshold, baseline algorithm + parameters, X-range, exclusion ranges, and peak templates (editable as a table via `st.data_editor`, add/remove rows freely). Replaces hand-editing an Excel file.
- `src/io/preset_store.py`: JSON load/save for `src/presets/materials.json`, the new preset store (replaces `src/io/preset_parser.py`'s Excel parsing).

### Changed
- **Material presets are now embedded in the app, not loaded from an Excel file.** The sidebar's Material Presets section is now just a "Select Material" dropdown reading live from `src/presets/materials.json` — the Browse Preset File / Reload Presets / clear (✖️) buttons and the Excel file-path caption are gone. Add or edit materials on the new Material Presets page instead.
- **View Options moved to the very bottom of the sidebar** (after Loaded Files), instead of sitting between Batch Export and Reset to Raw.
- The 4 existing presets (WSe2_PL, WSe2_Raman, MoS2_Raman, Silicon_Raman) were migrated as-is into `src/presets/materials.json`.

### Removed
- **`presets/` folder removed**: `material_presets.xlsx`, `create_template.py`, `README.md`. **`src/io/preset_parser.py`** (Excel parsing) and its tests (`tests/unit/test_preset_parser.py`) removed along with it; `tests/conftest.py`'s now-unused `tmp_preset_xlsx` fixture removed too.
- **`PeakTemplate.amplitude` field dropped.** Verified dead: `src/processing/fitting.py` auto-estimates amplitude from the actual spectrum data at fit time and never consults the preset's value (this was already documented on `PeakDefinition.amplitude`). `to_peak_definition()` now passes a fixed placeholder instead.
- **`MaterialPreset.to_processing_settings()` removed** — zero call sites anywhere in `src/` or `tests/`; dead code.
- **`PresetLibrary` class removed** from `src/models/preset.py`. It existed to wrap Excel's sheet-name-based lookup (`get_preset()` parsed a `"Material_Mode"` string back into two fields via `parse_sheet_name()`); JSON presets already have `material_name`/`mode` as separate fields, so callers now use a plain `dict[(material_name, mode), MaterialPreset]` directly — no parsing round-trip, no wrapper class. `PresetLibrary.last_loaded` (set on construction, never read anywhere) is gone with it.
- `validate_preset_schema()` and `parse_sheet_name()` (both Excel-specific, in the deleted `preset_parser.py`) — superseded by `MaterialPreset.validate()`, reused directly by the new editor's save action. `parse_exclusion_ranges()` was *not* dead (still used by `auto_workflow.py` for the exclusion-ranges feature) — it moved to `src/models/preset.py` instead of being deleted, with its pandas `NaN` check simplified since JSON never produces one.
- `get_sheet_count()` — repurposed as a "N material(s) configured" caption on the new Material Presets page rather than deleted outright.

## [2.10.0] - 2026-08-12

### Removed
- **Project save/load removed.** The sidebar's "Project" section (Save Project button and the "Load Project" `st.file_uploader`, including its `_loaded_project_file_id` re-run guard) is gone from `src/ui/sidebar.py`. `src/io/project_io.py` (`save_project()`/`load_project()`) is untouched and still covered by `tests/unit/test_project_io.py` — only the sidebar UI call sites were removed.
- **Plot preview removed from Export.** The composite plot no longer renders on screen before download. `plot_composite()` is still built internally so PNG/HTML Quick Export keeps working — it's just never passed to `render_plot()`.
- **Right-hand control panel removed.** `src/ui/control_panel/` (View Options, Export, Reset to Raw) is deleted; `app.py` no longer splits into `col_center`/`col_right` — the plot now takes the full width next to the sidebar.

### Changed
- **Quick Export, Batch Export, View Options, and Reset to Raw moved into the sidebar** (`src/ui/sidebar.py`), placed right after the Material Presets section (below the Run Auto-Workflow / Run All Files buttons), so the whole workflow — presets, run, export, view/reset, load/manage files — lives in one place. The pre-fit placeholder shortened to "Run Auto-Workflow to enable export." since it now sits directly under those buttons.
- "Load Spectra" (Browse Spectrum Files) and "Loaded Files" (current-file info, Remove File / Delete All) are unchanged and remain in the sidebar, now below the export/view/reset block.

## [2.9.0] - 2026-08-12

### Removed
- **Manual step-by-step processing UI removed.** The accordion's Processing Range, De-spiking, Baseline Correction, and Peak Fitting sections (`src/ui/control_panel/processing_range.py`, `despike.py`, `baseline.py`, `peak_fit.py`, `shared.py`) are gone. Processing a spectrum is now done exclusively through the sidebar's Material Preset **Run Auto-Workflow** / **Run All Files** buttons (`execute_auto_workflow()` in `src/processing/auto_workflow.py`), which already existed and needed no changes. The control panel now only shows View Options, Export, and Reset to Raw.
- **Export section's "Advanced Options" (detailed per-point CSV) dropped.** `export_single_spectrum_csv()` itself is untouched in `src/io/export.py` (and still covered by `tests/unit/test_export.py`) — only its UI call site was removed. Quick Export (PNG/HTML/CSV fit parameters) and Batch Export (master CSV across files) are unchanged.

### Changed
- The Export section is no longer step "5️⃣" of an accordion — `render_export_section()` lost its `is_expanded` parameter and outer `st.expander(...)` wrapper, since it's now the panel's only content.
- Sidebar now expands by default (`initial_sidebar_state="expanded"`) since it's the only place processing can be started from.
- `tests/unit/test_control_panel_baseline.py` removed (tested the deleted `control_panel/baseline.py` UI module; `tests/unit/test_baseline.py`, which tests the underlying `src/processing/baseline.py` algorithms used by `auto_workflow.py`, is unaffected).
- `USER_GUIDE.md`, `README.md`, `Summary.md` updated to describe the preset/auto-workflow-only flow; the now-inapplicable "Using SpectralFit (Manual Workflow)" section was removed from `USER_GUIDE.md`.

## [2.8.0] - 2026-08-12

A maintainability and correctness pass: no user-facing features were added, but several real bugs were fixed (including two that could crash or hang the app), the codebase gained its first automated test suite, and the largest UI module was split apart for maintainability.

### Fixed
- **"Load Project" crashed on every use** (`src/ui/sidebar.py`): `load_project()` returns a `(files, plot_width_preset)` tuple, but the call site assigned the whole tuple to `st.session_state["files"]` without unpacking it, so the plot immediately crashed with `AttributeError: 'tuple' object has no attribute 'keys'`.
- **Fixing the above exposed an infinite-rerun loop**: `st.file_uploader`'s value stays truthy across reruns until the file is removed or replaced. The handler had no guard, so it re-processed the same upload — including its own `st.rerun()` — on every rerun, forever, and the app never rendered past the sidebar. Fixed by tracking the uploaded file's stable `.file_id` and only processing it once.
- **Whitespace-delimited spectrum files were completely broken** (`src/processing/parser.py`): the whitespace-delimiter fallback used `pd.read_csv(..., delim_whitespace=True)`, a kwarg removed in the installed pandas version, so it raised `TypeError` on every attempt — silently swallowed by the surrounding delimiter-sniffing loop.
- **Missing spectrum files reported the wrong error**: because of the same swallowed-exception loop, a genuinely missing file surfaced as a generic "File must have at least 2 columns" `ValueError` instead of `FileNotFoundError`. Fixed by checking file existence explicitly before the delimiter loop.
- **Non-functional mobile-detection code removed** (`app.py`, `control_panel/__init__.py`): the injected JavaScript viewport-detection block could never actually communicate back to Python (Streamlit doesn't support that callback), so `is_mobile` was permanently `False` and an entire unreachable mobile-layout code path existed. Removed; the app now has a single (the only reachable) desktop layout.
- **Broken footer links** (`app.py`): "Documentation" pointed at a file deleted in an earlier commit; "Report Issues" pointed at a `your-repo` placeholder URL. Both now point at the real repository.
- **Confusing peak-count logic simplified** (`src/processing/fitting.py`): `auto_find_peaks()`'s peak-selection formula looked like it enforced a `min_peaks` floor but never actually could (Python slicing silently truncates) — simplified to what it actually computes, with output unchanged.

### Added
- **Automated test suite**: `pytest` configured via `pyproject.toml`; 119 unit tests added under `tests/unit/` covering despiking, all 5 baseline algorithms, Voigt fitting, spectrum/preset parsing, CSV/project export and import, and stale-fit detection. Previously the project had zero automated tests.

### Changed
- **`src/ui/control_panel.py` (2,687 lines) split into a package**, `src/ui/control_panel/`, one module per accordion section (`processing_range.py`, `despike.py`, `baseline.py`, `peak_fit.py`, `export.py`) plus `shared.py` for cross-section helpers. The public interface (`render_control_panel()`) is unchanged.
  - Deduplicated the baseline algorithm dispatch, which was previously implemented three times (parameter widgets, live preview, and the real run) with drift risk between preview and applied results — now a single `_run_baseline_algorithm()` helper used by both preview and run paths.
  - Consolidated the repeated `show_raw`/`show_despiked`/`show_corrected`/`show_fit`/`show_components`/`show_residuals` session-state rewrite (previously duplicated near-verbatim across all 5 sections) into a single `_set_view_stage()` helper.
  - `compute_preprocessing_hash()` / `mark_fit_stale_if_needed()` moved to a new `src/utils/fit_staleness.py`, fixing a layering violation where `src/processing/auto_workflow.py` (a processing-layer module) had to import from the UI layer to reach them.
- **Dead code removed**: 6 unused UI modules (`file_panel.py`, `control_panel_old.py`, `export_tab.py`, `fit_tab.py`, `preprocess_tab.py`, `components.py`, ~1,300 lines) plus 3 unreachable functions in `src/visualization/plotter.py` (`plot_preview`, `plot_with_baseline`, `apply_plot_width`) that had no callers anywhere in the repo.
- **Documentation consolidated**: `FITTING_IMPROVEMENTS.md` merged into `Fitting_Algo.md` as a dated implementation-history section (it was a near-duplicate changelog for work already described there); the version-history content that had been triplicated across `README.md`, `Summary.md`, and this file is now only here; `Summary.md` trimmed to focus on architecture/data-model/decisions (its stale project-structure tree and data-model code samples were also corrected to match the current code).

## [2.7.1] - 2026-05-31

### Added
- **Auto-update on launch**: `start.bat` (Windows) and `start.sh` (macOS/Linux) now pull the latest version from GitHub each time they run, so anyone who cloned the repo always launches the newest release. The check runs `git pull --ff-only` from the repo root, reinstalls any changed dependencies, then starts the app.
- **Never blocks**: if Git isn't installed, the copy isn't a git checkout (e.g. a ZIP download), or the network/GitHub is unavailable, the launcher prints a short notice and starts the version you already have.

### Changed
- README install instructions now recommend `git clone` (for auto-updates) with a manual-setup fallback, and note that ZIP downloads don't auto-update.

### Added
- **"Save Master CSV to folder" button** in the Export section's Batch Export block. Opens a native OS Save-As dialog **pre-pointed at the folder the raw `.txt` data was loaded from**, with an **editable filename**, and writes the master CSV directly there — no more browser-Downloads detour. The existing in-browser "Download Master CSV" button is retained as a fallback.
- New `source_dir` field on `SpectrumFile` records the folder each spectrum was loaded from (captured by the Browse picker). Backward-compatible: old project JSON without this field loads fine (defaults to `None`).
- New reusable `prompt_save_path()` helper in `src/io/export.py` wrapping `tkinter.filedialog.asksaveasfilename` in a subprocess (same pattern as the Browse-files dialog).

## [2.6.0] - 2026-05-30

### Added
- **"Delete All Files" button** in the sidebar's "Loaded Files" section. A single click clears every loaded spectrum at once (wired to the existing `clear_all_files()` helper), instead of removing files one by one. Placed side-by-side with the existing "Remove File" button via a two-column layout.

## [2.5.0] - 2026-05-16

### Added
- **Multi-select file picker** for spectrum input: the sidebar now exposes a **"Browse Spectrum Files"** button that opens a native OS multi-select dialog (`tkinter.filedialog.askopenfilenames`), filtered to `.txt` with an "All files" fallback. Ctrl-click / Cmd-click to pick multiple files in one dialog session.
- Last-picked directory is remembered as the next dialog's starting location (session-state key `'last_picked_dir'`).
- Pop-based reload guard via a transient `'pending_files_to_load'` session-state queue — picked files are parsed exactly once on the next rerun; no per-rerun re-parsing.

### Changed
- **Sidebar "Load Spectra" block fully replaced**: the "Folder Path" text input and "Browse File Folder" button are removed. The new picker preserves all downstream behavior (multi-Y `__1`/`__2` splitting, `detect_mode_from_filename` auto-detection, per-file duplicate skipping, per-file error isolation).
- Subprocess output for the new picker is **JSON-serialized** (rather than bare `print()`) so picked paths with spaces, commas, or unicode round-trip safely.
- **PL "Raw" summary row** in the fit-results table is now rendered **at the top** of the table instead of the bottom — applies to both the in-app table ([src/visualization/unified_plot.py](src/visualization/unified_plot.py)) and the exported master CSV ([src/io/export.py](src/io/export.py)). Easier raw-vs-fit comparison.
- Sidebar success message reads `"Loaded N file(s)"` (dropped the "from folder" suffix).

### Removed
- Session-state keys `'last_folder_path'` and `'loaded_folder_path'` (replaced by `'last_picked_dir'` and `'pending_files_to_load'`). These keys were never written to project JSON, so existing saved projects load unchanged.

## [2.4.1] - 2026-02-02

### Changed
- **Removed Display Settings UI** from sidebar - plot width now defaults to Full (100%) everywhere
- **Moved Fit Results table** from right-side control panel to below the spectrum plot in center column
- **Removed "Residuals" subplot title** that overlapped with x-axis labels (y-axis label retained)

### Fixed
- All `plot_width_preset` defaults updated from "Standard" to "Full" across codebase

## [2.3.0] - 2026-01-08

### Added
- **Material Preset System**: Excel-driven, one-click auto-workflow (X-range → Despike → Baseline → Fitting) across a full pipeline. Sheet-per-material design (e.g. "Graphene_Raman", "MoS2_Raman"), auto-discovered from sheet names; mode validation prevents applying a Raman preset to a PL file. No code changes needed to add a new material — see [presets/README.md](presets/README.md) for the Excel schema. Batch-processing 10+ files with identical parameters now takes seconds instead of minutes.

### Changed
- **Auto-Workflow rewritten** to replicate the exact manual step-by-step workflow instead of taking shortcuts. Previously it used `original_data` (instead of `raw_data`) as the X-range source, didn't reset flags or clear previews correctly, and didn't mark fits stale after preprocessing changes. It now updates both `raw_data` and `processed_data`, resets flags, clears previews, marks fits stale, and updates view options at every stage — producing identical results to manual processing.

### Fixed
- **Despike tuple-unpacking bug** in auto-workflow: `remove_spikes()` returns `(y_clean, spike_mask)`, but the whole tuple was being assigned to the Y array, which numpy then coerced into an invalid 2D array. Fixed by unpacking both return values.
- **ALS baseline parameter name mismatch**: auto-workflow called the ALS functions with `lam=` instead of the actual keyword `lambda_=`, silently halting the pipeline at the baseline stage.
- **Sparse matrix format error** ("spsolve requires A be CSC or CSR matrix format"): added `A = A.tocsc()` before all three `spsolve()` calls in `baseline.py`, fixing ALS, Rolling Ball, and airPLS.
- **Preset file not found**: the default preset path was relative and broke depending on the working directory the app was launched from. `get_default_preset_path()` now resolves an absolute path via `Path(__file__).resolve()`.
- **X-range validation crash** ("StreamlitValueBelowMinError"): a saved `x_min` from a preset could be slightly below the actual data minimum (floating-point precision). Added clamping so X-range inputs always stay within the current data's bounds.

## [2.2.1] - 2025-12-23

### Added
- **Real-time preview for baseline correction** - See red dashed baseline preview before applying
- **Real-time preview for de-spiking** - See orange dashed preview of spike removal
- **X-range processing** - Crop spectrum to specific region before processing
- **Improved peak fitting algorithm** with critical fixes:
  - Fixed amplitude initialization (convert peak height to integrated intensity)
  - Shape-aware width initialization using Gaussian/Lorentzian mixing
  - Adaptive parameter bounds (wider tolerance for broader peaks)
  - Improved auto-find FWHM estimation with curvature-based fallback
  - Peak overlap detection with actionable warnings
- **Enhanced UI/UX**:
  - Simplified View Options with organized checkbox groups
  - Auto-managed plot layer visibility at each processing stage
  - Removed left file panel - plot now takes 70% width
  - File navigation dropdown with left/right buttons at top of plot
  - Scrollable control panel (800px height)
  - Reordered workflow sections for better flow
- **Algorithm documentation**:
  - Comprehensive Baseline_Algo.md (algorithm analysis)
  - Comprehensive Fitting_Algo.md (algorithm deep dive)
  - FITTING_IMPROVEMENTS.md (v2.2.1 enhancement summary)

### Changed
- **Plot visibility behavior** (auto-managed):
  - X-range stage: Show only "Raw" curve
  - Despike stage: Show "Raw" AND "De-spiked" for comparison
  - Baseline stage: Show "De-spiked" AND "Preview baseline" (red dashed)
  - Peak fit stage: Show "Corrected", "Fit Total", and optionally "Components"
- **Removed "Preview Corrected" green curve** from baseline preview (user request)
- **UI section order**: Processing Range → De-spiking → Baseline → Peak Fitting → Export → Reset to Raw → View Options
- **Amplitude bounds**: Increased from 2× to 5× max intensity (accounts for sharp peaks)

### Fixed
- **Critical crash fixes**:
  - Peak deletion IndexError when deleting non-consecutive rows (P0)
  - Peak addition TypeError when clicking "+" button (P0)
- **Behavioral fixes**:
  - Reset to Raw now restores original data (before X-range cropping)
  - Plot layers automatically clear when advancing to next processing stage
  - Preview states cleared after fitting runs (no stray preview curves)
- **Parameter fixes**:
  - Despike sensitivity range extended to 30.0 (was 15.0)
- **Fitting algorithm improvements**:
  - Fixed amplitude initialization (critical: lmfit expects integrated intensity, not peak height)
  - Fixed parameter extraction to handle both Parameter objects and floats
  - Fixed component curve evaluation (use kwargs not params dict)
  - Fixed FitResult validation (allow empty peaks when failed)
  - Fixed baseline parameter naming (lambda_ not lam)

### Quality Improvements
- **Expected R² improvement**: 0.85-0.92 → 0.95-0.99 (for well-behaved spectra)
- **Convergence rate improvement**: 60-70% → 90-95%
- **Bound-hitting issues**: Common → Rare
- **Auto-find quality**: Poor → Good

## [2.2.0] - 2025-12-20

### Added
- **Single-page, three-panel layout** (files/plot/controls)
- **X-range cropping** with data masking
- **Real-time preview** for despike and baseline operations
- **Full peak fitting** with Voigt models
- **Sequential workflow** with auto-expand accordion
- **Unified multi-layer plot** visualization
- **Processing Range section** with X-min/X-max controls
- **De-spiking section** with threshold slider
- **Baseline Correction section** with algorithm selection (Polynomial, ALS, Rolling Ball, Spline, airPLS)
- **Peak Fitting section** with auto-find and manual peak management
- **View Options section** with layer visibility controls
- **Status tracking** with progress badges in file cards
- **Stale fit detection** using hash-based preprocessing change tracking

### Changed
- Migrated from multi-tab layout to single-page accordion layout
- Desktop layout: 70% plot width, 30% control panel
- Mobile layout: Stacked vertical (controls → plot)

## [2.1.0] - 2025-12-19

### Added
- Real-time baseline preview with instant parameter feedback
- Auto mode detection from filename patterns (RM*/PL*)
- Plot width control (Compact/Standard/Wide/Full presets)
- Negative Y value support with automatic shifting
- Enhanced export with new metadata columns

## [2.0.0] - 2025-12-18

### Added
- Initial release of SpectralFit v2.0
- Raman and Photoluminescence spectrum analysis
- Cosmic-ray spike removal (modified Z-score)
- Baseline correction (Polynomial, ALS)
- Multi-peak Voigt profile fitting
- Interactive Plotly visualizations
- Batch processing support
- Project save/load (JSON)
- CSV export for fit results

---

## Version History Summary

- **v2.9.0** (2026-08-12): Removed the manual step-by-step processing UI — spectra are now processed exclusively via the sidebar's Material Preset Run Auto-Workflow; the control panel shows only View Options, Export, and Reset
- **v2.8.0** (2026-08-12): Bug-fix and maintainability pass — fixed a crash and an infinite-loop bug in project loading, fixed broken whitespace-delimited file parsing, added a 119-test pytest suite, split `control_panel.py` into a package, removed dead code, consolidated documentation
- **v2.7.1** (2026-05-31): Launchers auto-update from GitHub on each run (with offline/ZIP fallback)
- **v2.7.0** (2026-05-30): "Save Master CSV to folder" — native Save-As dialog writes the master CSV into the raw-data folder with a user-typed filename
- **v2.6.0** (2026-05-30): "Delete All Files" button in the sidebar to clear all loaded spectra at once
- **v2.5.0** (2026-05-16): Multi-select file picker replaces folder picker; PL Raw row moved to top of fit-results table
- **v2.4.1** (2026-02-02): Display Settings removed (plot width defaults to Full); Fit Results moved below plot
- **v2.4.0** (2026-01-XX): Batch auto-workflow ("Run All Files") + smart file navigation
- **v2.3.0** (2026-01-08): Material Preset System (Excel-based auto-workflow)
- **v2.2.1** (2025-12-23): Critical fitting algorithm improvements + UI refinements
- **v2.2.0** (2025-12-20): Single-page accordion layout + real-time previews
- **v2.1.0** (2025-12-19): Real-time baseline preview + auto mode detection
- **v2.0.0** (2025-12-18): Initial release
