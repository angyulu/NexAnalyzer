# SpectralFit v2.5.0 - Project Summary

## Overview

SpectralFit is a desktop web application for analyzing Raman and Photoluminescence (PL) spectroscopy data. Built with Streamlit and Python, it provides real-time previews, advanced peak fitting, material-preset-driven automation, and a streamlined single-page accordion workflow.

---

## Recent Updates (v2.5.0)

### New Features ⭐

#### 1. Multi-Select File Picker (replaces folder picker)
**What Changed:** The "Browse File Folder" button is gone. In its place, **"Browse Spectrum Files"** opens a native OS multi-select file dialog.

**Why:** Loading a whole folder of `.txt` files was awkward when the user only wanted a subset, had files scattered across folders, or just wanted to drop in a single file to check.

**Behavior:**
- Multi-select dialog filtered to `.txt` by default, with "All files" fallback
- Picked files are queued and parsed once on the next rerun (no per-rerun re-parsing)
- Last-picked directory is remembered as the next dialog's `initialdir`
- Cancel = clean no-op (no error, no rerun loop)
- Re-picking already-loaded files is skipped silently with a count
- Multi-Y files continue to split into `name__1.txt`, `name__2.txt`, ... entries
- Multi-file paths are JSON-serialized across the subprocess boundary so paths with spaces, commas, or unicode survive intact

**Files Modified:** [src/ui/sidebar.py](src/ui/sidebar.py) (`render_sidebar`, "Load Spectra" block)

**Session State Changes:**
- Removed: `'last_folder_path'`, `'loaded_folder_path'`
- Added: `'last_picked_dir'` (str, seeds next dialog's start location), `'pending_files_to_load'` (transient queue, consumed once per pick)

#### 2. Fit Results Table — Raw Row at Top (PL mode)
The "Raw" summary row (max intensity, position, FWHM at half-max from the processed spectrum) now appears at the **top** of the fit-results table instead of the bottom, both in the in-app table ([src/visualization/unified_plot.py](src/visualization/unified_plot.py)) and in the exported master CSV ([src/io/export.py](src/io/export.py)). Makes the raw vs. fit comparison easier to scan at a glance.

---

## Previous Updates (v2.3.0)

### New Features ⭐

#### 1. Material Preset System
**What It Does:** Excel-based automation for complete processing workflows.

**Key Features:**
- **One-click auto-workflow**: Complete pipeline execution (X-range → Despike → Baseline → Fitting) from preset
- **Sheet-per-material design**: Each material gets its own sheet (e.g., "Graphene_Raman", "MoS2_Raman")
- **Auto-discovery**: Materials automatically loaded from Excel sheet names
- **Mode validation**: Ensures Raman presets only apply to Raman files (prevents unit mismatches)
- **Excel-based configuration**: No code changes needed to add new materials

**User Workflow:**
1. Create preset in `SpectralFit/presets/material_presets.xlsx` (or use provided examples)
2. Load spectrum files in app
3. Click "🔄 Reload Presets" in sidebar
4. Select material from dropdown (e.g., "Graphene_Raman")
5. Click "🚀 Run Auto-Workflow" → entire pipeline executes automatically
6. Results displayed with R² and χ² metrics

**Excel Schema:**
- **Processing Settings** (Row 1-2): x_range, despike_threshold, baseline_algorithm, baseline parameters
- **Peak Templates** (Row 4+): peak_label, center, center_tolerance, amplitude, width_fwhm, shape, color

**Impact:** Batch processing 10+ files with identical material parameters now takes seconds instead of minutes.

**Documentation:** See [presets/README.md](SpectralFit/presets/README.md) for Excel schema and examples.

#### 2. Auto-Workflow Rewrite (Critical Behavior Change)
**What Changed:** Auto-workflow now replicates exact manual user workflow instead of taking shortcuts.

**Old Behavior (v2.2.1 and earlier):**
- Used `original_data` as source for X-range (incorrect)
- Didn't reset flags properly after X-range application
- Skipped session state updates
- Didn't mark fits as stale after preprocessing changes
- Set `x_range_enabled=True` (should be False after applying)

**New Behavior (v2.3.0):**
- **X-Range**: Uses `raw_data` as source, updates BOTH `raw_data` and `processed_data`, resets flags, clears previews
- **Despike**: Saves threshold, unpacks tuple correctly, marks fit stale, clears preview, updates view options
- **Baseline**: Routes to correct algorithm, saves y_shift, marks fit stale, clears preview, updates view options
- **Fitting**: Converts templates, computes hash, clears previews, updates all session state

**Impact:** Auto-workflow now produces IDENTICAL results to manual step-by-step processing. All edge cases and state management logic are preserved.

### Critical Bug Fixes ✅

#### 1. Tuple Unpacking Error in Despike (CRITICAL)
**Error:** "X and Y must be 1D arrays" during auto-workflow despike stage

**Root Cause:**
- `remove_spikes()` returns tuple `(y_clean, spike_mask)`
- Code assigned entire tuple to `Y_despiked` variable
- When passed to `SpectrumData`, numpy converted tuple to 2D array
- Validation rejected 2D array

**Fix:** Changed `Y_despiked = remove_spikes(...)` to `Y_despiked, spike_mask = remove_spikes(...)`

**Impact:** Auto-workflow now completes despike stage successfully.

#### 2. ALS Baseline Parameter Name Mismatch
**Error:** Auto-workflow stopped at baseline with no clear error message

**Root Cause:** Code used `lam=preset.baseline_lambda` but function expects `lambda_=`

**Fix:** Changed all ALS calls to use `lambda_=preset.baseline_lambda`

**Impact:** ALS baseline now works in auto-workflow.

#### 3. Sparse Matrix Format Error
**Error:** "spsolve requires A be CSC or CSR matrix format"

**Root Cause:** Matrix A wasn't converted to CSC/CSR format before calling scipy's `spsolve()`

**Fix:** Added `A = A.tocsc()` before all 3 `spsolve()` calls in [baseline.py](src/processing/baseline.py) (lines 224, 465, 729)

**Impact:** ALS, Rolling Ball, and airPLS algorithms now work correctly.

#### 4. Preset File Not Found
**Error:** "❌ Preset file not found: SpectralFit/presets/material_presets.xlsx"

**Root Cause:** Default path was relative, failed depending on working directory

**Fix:** Created `get_default_preset_path()` in [session_state.py](src/ui/session_state.py) using `Path(__file__).resolve()` for absolute path

**Impact:** Preset path now works regardless of where app is launched from.

#### 5. Number Input Validation Error
**Error:** "StreamlitValueBelowMinError: The value 100.0 is less than the min_value 100.874"

**Root Cause:** Saved x_min (100.0 from preset) was less than actual data minimum (100.874)

**Fix:** Added clamping logic in [control_panel.py](src/ui/control_panel.py):
```python
x_min_value = max(x_min_value, x_min_data)
x_max_value = min(x_max_value, x_max_data)
```

**Impact:** X-range inputs now always stay within valid data bounds.

---

## Core Features

### Data Processing
- **Data Ingestion**: Load two-column .txt spectrum files (X, Y)
- **X-Range Processing**: Crop spectrum to specific region before analysis
- **De-spiking**: Cosmic-ray spike removal with real-time preview (modified Z-score algorithm)
- **Baseline Correction**: Real-time preview for Polynomial, ALS, Rolling Ball, Spline, airPLS algorithms
  - **NEW**: "None (Skip)" option for ultra-wide PL peaks
- **Peak Fitting**: Multi-peak Voigt profile fitting with:
  - Auto-find peak detection
  - Shape-aware initialization (Gaussian/Lorentzian mixing)
  - Adaptive parameter bounds
  - Overlap detection with warnings
- **Material Preset System** ⭐ NEW in v2.3.0:
  - Excel-based presets for common materials
  - One-click auto-workflow execution
  - Sheet-per-material design (easy to add new materials)
  - Mode validation (Raman/PL)
  - No code changes needed to add materials

### Visualization & UX
- **Single-Page Accordion Workflow**: Streamlined sequential processing
- **Real-Time Previews**: See de-spiking and baseline effects before applying
- **Auto-Managed Plot Layers**: Visibility automatically adjusts per processing stage
- **Interactive Plotly Plots**: Publication-quality with zoom, pan, export
- **File Navigation**: Dropdown + Previous/Next buttons (recently fixed)
- **Batch Processing**: Load and process multiple files independently
- **Project Persistence**: Save/load full project state to JSON
- **Multi-Select File Picker** ⭐ NEW in v2.5.0: Native OS file dialog with multi-select, `.txt` filter, and last-picked-directory memory (replaces v2.3.0 folder picker)

### Plot Layer Visibility (Auto-Managed)
- **Processing Range**: Only "Raw" data
- **Despike**: "Raw" AND "De-spiked" (comparison)
- **Baseline**: "De-spiked" AND "Preview baseline" (red dashed, comparison)
- **Peak Fit**: "Corrected", "Fit Total", "Components"

Users can override manually in **View Options**.

---

## Technical Architecture

### Frontend
- **Framework**: Streamlit (Python web framework for data apps)
- **Layout**: Three-panel desktop layout (files → plot → controls)
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
SpectralFit/
├── app.py                          # Main Streamlit application
├── src/
│   ├── models/
│   │   ├── spectrum.py             # SpectrumFile, ProcessingSettings, FitResult
│   │   └── peak.py                 # PeakDefinition, parameter bounds
│   ├── processing/
│   │   ├── parser.py               # Two-column .txt file parsing
│   │   ├── despiking.py            # Modified Z-score spike removal
│   │   ├── baseline.py             # 5 baseline algorithms + quality metrics
│   │   └── fitting.py              # Voigt peak fitting with Levenberg-Marquardt
│   ├── ui/
│   │   ├── sidebar.py              # Mode toggle, file upload, project I/O
│   │   ├── control_panel.py        # Accordion workflow (X-range → Despike → Baseline → Fit → Export)
│   │   └── session_state.py        # Session state management
│   ├── visualization/
│   │   ├── unified_plot.py         # Multi-layer plot with file navigation
│   │   └── plotter.py              # Plot generation utilities
│   └── io/
│       └── project_io.py           # JSON save/load with numpy array serialization
└── requirements.txt                # Python dependencies
```

---

## Workflow Guide

### 1. Load Data
- Click **Browse Spectrum Files** in the sidebar and pick one or more `.txt` files (multi-select, two-column or multi-Y format)
- Mode auto-detection from filename (RM* → Raman, PL* → PL)
- Or manually select mode (Raman/PL)

### 2. Select File
- Use dropdown or Previous/Next buttons in plot header
- Progress indicators show processing status per file

### 3. Processing Range (Optional)
- Crop spectrum to specific X-range
- Data masking approach (preserves original)

### 4. De-spiking (Optional)
- Real-time preview with threshold slider
- Modified Z-score algorithm
- Apply when satisfied with preview

### 5. Baseline Correction
- **For Raman (narrow peaks)**: Use Polynomial, ALS, Rolling Ball
- **For PL (ultra-wide peaks)**: Use "None (Skip)" if peak IS the signal
- Real-time preview for all algorithms
- Quality metrics displayed after correction

### 6. Peak Fitting
- Auto-find peak detection (curvature-based FWHM estimation)
- Manual peak addition/deletion/editing
- Voigt profile fitting with shape parameter (0.0 = Gaussian, 1.0 = Lorentzian)
- Overlap detection warns when peaks closer than 2× average FWHM
- R² and χ² goodness-of-fit metrics

### 7. Export
- Save plots as PNG/SVG
- Export fit results to CSV (with residuals and component curves)
- Save full project to JSON (all files + processing state)

---

## Data Model

### SpectrumFile
```python
@dataclass
class SpectrumFile:
    filename: str                           # Original filename
    mode: Literal["Raman", "PL"]           # Spectroscopy mode
    original_data: SpectrumData            # True original (never modified)
    raw_data: SpectrumData                 # After X-range cropping
    processed_data: SpectrumData           # After despike + baseline
    processing_settings: ProcessingSettings # Parameters for all algorithms
    fit_result: Optional[FitResult]        # Peak fitting results
    peak_table: List[PeakDefinition]       # User-defined peaks
    # Status flags
    despike_done: bool
    baseline_done: bool
    fit_done: bool
    x_range_enabled: bool
```

### Processing Settings
```python
@dataclass
class ProcessingSettings:
    # De-spiking
    despike_threshold: float = 5.0
    despike_window: int = 5

    # Baseline
    baseline_algorithm: str = "Polynomial"
    baseline_poly_degree: int = 3
    baseline_als_lambda: float = 10000.0
    baseline_als_p: float = 0.001
    # ... (other algorithm parameters)

    # X-range
    x_min: Optional[float] = None
    x_max: Optional[float] = None
```

### FitResult
```python
@dataclass
class FitResult:
    success: bool                          # Fit converged
    r_squared: float                       # Goodness-of-fit
    chi_squared: float                     # Reduced χ²
    fitted_peaks: List[FittedPeak]         # Optimized peak parameters
    fit_total: SpectrumData                # Total fit curve (sum of peaks)
    residuals: SpectrumData                # Data - Fit
    component_curves: List[SpectrumData]   # Individual peak curves
```

---

## Key Technical Decisions

### 1. Three-Layer Data Model
- **original_data**: Preserves true original before any processing (Issue #5 fix)
- **raw_data**: After X-range cropping (reset point for despike/baseline)
- **processed_data**: After all processing (used for peak fitting)

**Rationale:** Allows "Reset to Raw" to restore full original dataset, not just cropped version.

### 2. Real-Time Preview with Session State Caching
- Preview calculations stored in `st.session_state['baseline_preview']`
- Prevents recalculation on every widget interaction
- Non-destructive workflow (preview → apply)

**Rationale:** Improves performance and user experience for iterative parameter tuning.

### 3. Accordion Workflow with Auto-Expand
- `st.session_state['expanded_section']` tracks current stage
- Sections auto-expand when previous stage completes
- Sequential workflow guides users through pipeline

**Rationale:** Reduces cognitive load for new users, prevents skipping critical steps.

### 4. Mode-Aware Parameter Bounds
- Raman: Center tolerance ±5 cm⁻¹, spectral resolution 1-2 cm⁻¹
- PL: Center tolerance ±30 nm, spectral resolution 1-5 nm
- Adaptive FWHM bounds: 0.5× to 3× initial guess

**Rationale:** Prevents parameter runaway, improves convergence rate (60-70% → 90-95%).

### 5. Selectbox On-Change Callback for Navigation
- Previous approach: Button updates state → `st.rerun()` → race condition
- Current approach: Button updates state → selectbox callback handles rerun
- No manual `st.rerun()` calls in button handlers

**Rationale:** Fixes race condition between button handlers and selectbox widget evaluation.

### 6. "None (Skip)" Baseline Option
- Physically accurate for PL emission spectra (peak IS the signal)
- Avoids fighting algorithms when no background exists
- Marks baseline stage as "done" to advance workflow

**Rationale:** 70%+ peak coverage violates baseline algorithm assumptions (peaks = narrow noise).

---

## Known Issues & Limitations

### Current Limitations:
1. **No recursive folder scan**: Users pick individual files (or multi-select within one dialog session); subtree walking is not supported
2. **Cloud deployment constraints**: The native tkinter file picker only works on local Streamlit installations (not Streamlit Cloud / headless servers)

### Resolved Issues (v2.2.1):
- ✅ **Issue 1**: Peak deletion IndexError (iterrows() vs. iloc mismatch)
- ✅ **Issue 2**: Peak addition TypeError (None-check guard)
- ✅ **Issue 3**: Plot layer visibility (auto-reset session state)
- ✅ **Issue 4**: Despike sensitivity range (extended to 30.0)
- ✅ **Issue 5**: Reset to Raw data loss (original_data field)
- ✅ **Issue 6**: UI reordering, scroll bar, file navigation
- ✅ **Navigation button race condition**: Fixed with on_change callback
- ✅ **PL wide peak baseline issue**: Fixed with "None (Skip)" option

---

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Setup
```bash
# Clone repository
git clone <repo-url>
cd SpectralFit

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
streamlit run app.py
```

Application opens at `http://localhost:8501`.

---

## File Format

Two-column .txt files:
- **Column 1**: Wavenumber (cm⁻¹) for Raman, Wavelength (nm) for PL
- **Column 2**: Intensity (arbitrary units)
- **Delimiter**: Tab or comma
- **No header row**

Example:
```
100.0	150.2
101.5	148.7
103.0	152.1
...
```

---

## Testing Recommendations

### Unit Tests (Needed):
1. **Parser**: Two-column format, edge cases (negative Y, unsorted X)
2. **De-spiking**: Modified Z-score algorithm, threshold sensitivity
3. **Baseline**: All 5 algorithms, quality metrics calculation
4. **Fitting**: Voigt profile, parameter bounds, convergence detection

### Integration Tests (Needed):
1. **Workflow**: X-range → Despike → Baseline → Fit (end-to-end)
2. **Project I/O**: Save/load with numpy array serialization, backward compatibility
3. **Session state**: File navigation, accordion workflow, view options

### User Testing (Completed):
- ✅ Navigation buttons (Previous/Next wrap-around)
- ✅ "None (Skip)" baseline for PL spectra
- ✅ Real-time preview for despike and baseline
- ✅ Peak fitting with auto-find and manual editing

---

## Documentation

- **[README.md](README.md)**: Quick start guide, features overview
- **[CHANGELOG.md](CHANGELOG.md)**: Version history (v2.2.1 improvements)
- **[Baseline_Algo.md](Baseline_Algo.md)**: Baseline correction algorithms (Polynomial, ALS, Rolling Ball, Spline, airPLS)
- **[Fitting_Algo.md](Fitting_Algo.md)**: Peak fitting theory (Voigt profile, Levenberg-Marquardt, initialization strategies)
- **[FITTING_IMPROVEMENTS.md](FITTING_IMPROVEMENTS.md)**: v2.2.1 fitting algorithm enhancements (amplitude initialization, shape-aware bounds)

---

## Version History

### v2.5.0 (2026-05-16) - Current Release
**Status:** Production Ready

**New Features:**
- **Multi-Select File Picker** ⭐: Native OS multi-select file dialog (`tkinter.filedialog.askopenfilenames`) replaces the v2.3.0 folder picker. Pick any subset of files across one or more folders; last-picked directory is remembered.
- **Fit Results — Raw Row at Top (PL)**: PL "Raw" summary row moved to the top of both the in-app fit-results table and the exported master CSV for easier raw vs. fit comparison.

**Files Modified:**
- `src/ui/sidebar.py`: Replaced folder browser with multi-select file picker; JSON-serialized subprocess output for safe multi-path round-trip; pop-based reload guard (`pending_files_to_load` queue)
- `src/visualization/unified_plot.py`: Reordered fit results table to prepend PL Raw row
- `src/io/export.py`: Reordered master CSV rows to prepend PL Raw row
- `presets/material_presets.xlsx`: Preset content tweaks

**Breaking Changes:**
- Removed session-state keys `'last_folder_path'` and `'loaded_folder_path'`. Projects saved on prior versions don't depend on these keys (they were sidebar-local), so no migration needed.

### v2.4.1 (2026-02-02)
- Removed Display Settings UI from sidebar (plot width now defaults to Full / 100%)
- Moved Fit Results table from right-side control panel to below the spectrum plot
- Removed overlapping "Residuals" subplot title

### v2.4.0 (2026-01-XX)
- Batch auto-workflow ("Run All Files") and smart file navigation (auto-show fit results on file switch)

**Release Date:** January 8, 2026
**Status:** Superseded

**New Features:**
- **Material Preset System** ⭐: Excel-based automation for common materials
- **Auto-workflow engine**: One-click processing (X-range → Despike → Baseline → Fitting)
- **Folder browser with path memory**: Load all .txt files from folder
- **Rewritten auto-workflow**: Now matches manual user process exactly

**Bug Fixes:**
- Fixed tuple unpacking in despike stage (CRITICAL - was causing 2D array error)
- Fixed ALS baseline parameter name (`lambda_` not `lam`)
- Fixed sparse matrix format for scipy.spsolve (added `.tocsc()`)
- Fixed X-range processing to use `raw_data` instead of `original_data`
- Fixed preset file path to use absolute path
- Added X-range input clamping to prevent validation errors
- Added fit staleness detection after each processing stage
- Added session state updates for view options and expanded sections

**Files Modified:**
- `src/processing/auto_workflow.py`: Complete rewrite to match manual workflow
- `src/processing/baseline.py`: Added `.tocsc()` for sparse matrix operations
- `src/ui/control_panel.py`: Added X-range clamping validation
- `src/ui/session_state.py`: Added `get_default_preset_path()`
- `src/ui/sidebar.py`: Added folder browser and material preset UI
- `src/io/preset_parser.py`: New file for Excel preset parsing
- `src/models/preset.py`: New file for MaterialPreset and PeakTemplate models

**Breaking Changes:**
- Auto-workflow now modifies spectrum object in-place matching manual workflow
- Requires `material_presets.xlsx` file in `SpectralFit/presets/` folder

### v2.2.1 (2025-12-28)
- **Critical fitting algorithm improvements** (50-80% better convergence)
- **Navigation button fix** (race condition resolved)
- **"None (Skip)" baseline option** (for ultra-wide PL peaks)
- **Documentation updates** (Fitting_Algo.md, FITTING_IMPROVEMENTS.md)

### v2.2.0 (2025-12-20)
- Single-page accordion workflow
- Real-time preview for despike and baseline
- X-range cropping with data masking
- Multi-layer plot visualization
- Unified plot with file navigation
- Batch processing with independent file states

### v2.1 (Earlier)
- Plot width control (Compact/Standard/Wide/Full)
- Auto mode detection from filename
- Real-time baseline preview
- Negative Y value support

---

## Quick Reference

### Keyboard Shortcuts
- None (Streamlit web app - no keyboard shortcuts)

### File Navigation
- **Dropdown**: Select any file from loaded list
- **◀ (Previous)**: Navigate to previous file (wraps around)
- **▶ (Next)**: Navigate to next file (wraps around)
- **Counter**: Shows "File X of Y"

### Plot Layer Toggles
- **Raw**: Original data (before any processing)
- **De-spiked**: After spike removal
- **Baseline-Corrected**: After baseline subtraction
- **Fit Total**: Sum of all fitted peaks
- **Peak Components**: Individual peak curves

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

## Contributing

(Add contribution guidelines)

---

## License

(Add license information)

---

## Contact

(Add contact information)

---

## Acknowledgments

- **Streamlit**: Web framework for data apps
- **Plotly**: Interactive visualization library
- **lmfit**: Levenberg-Marquardt optimization
- **NumPy/SciPy**: Scientific computing libraries

---

**Last Updated:** 2026-05-16
**Project Version:** v2.5.0
**Status:** Production-ready with Multi-Select File Picker and Material Preset System
