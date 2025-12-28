# SpectralFit v2.2.1 - Project Summary

## Overview

SpectralFit is a desktop web application for analyzing Raman and Photoluminescence (PL) spectroscopy data. Built with Streamlit and Python, it provides real-time previews, advanced peak fitting, and a streamlined single-page accordion workflow.

---

## Recent Updates (v2.2.1)

### Critical Fixes Completed

#### 1. File Navigation Button Fix ✅
**Problem:** Previous/Next file navigation buttons weren't working - clicking them had no effect.

**Root Cause:** Race condition between button handlers and selectbox widget:
- Button handlers updated `session_state['current_file']` and called `st.rerun()`
- On rerun, selectbox evaluated with NEW current_file but still reflected old visual selection
- Mismatch detection overwrote button's change

**Solution:** Restructured navigation logic ([unified_plot.py:413-456](src/visualization/unified_plot.py#L413-L456)):
- Removed `st.rerun()` calls from button handlers
- Added `on_change` callback to selectbox
- Let selectbox handle rerun automatically through callback

**Impact:** Navigation buttons now work correctly with wrap-around behavior.

#### 2. "None (Skip)" Baseline Correction Option ✅
**Problem:** PL spectra with ultra-wide peaks (70%+ coverage) cause baseline algorithms to follow the peak curve instead of background, making correction impossible.

**Solution:** Added "None (Skip)" option to baseline algorithm dropdown ([control_panel.py](src/ui/control_panel.py) - Baseline section):
- Allows users to skip baseline correction entirely
- Marks baseline stage as "done" and advances to Peak Fitting
- Physically accurate for PL emission spectra where the broad peak IS the signal (not background)

**User Workflow:**
1. Load PL file with wide emission peak
2. Run de-spiking (if needed)
3. Select "None (Skip)" for baseline algorithm
4. Click "Run Baseline Correction" → advances to Peak Fitting
5. Fit Voigt peaks directly to de-spiked data

**Impact:** Users can now analyze PL spectra with ultra-wide peaks without fighting baseline algorithms.

---

## Planned Features (Not Yet Implemented)

### Local File Browser with Folder Memory 📋

**User Request:** "Please only keep the browser file button and remove drag file function. For browser file, I want to remember the last open file address and read all the data from the selected folder."

**Status:** Comprehensive plan created but implementation NOT started (user stopped planning process).

**Technical Approach:**
- Replace Streamlit's `st.file_uploader()` with native OS folder picker (`tkinter.filedialog.askdirectory()`)
- Store last folder path in `~/.spectralfit_config.json` (persistent across sessions)
- Scan selected folder for ALL .txt files and load automatically
- Works only for local Streamlit installations (not cloud deployments)

**Planned Implementation:**
1. Create `src/utils/config.py` - Config file I/O (last folder path persistence)
2. Create `src/utils/file_browser.py` - Native folder dialog using tkinter
3. Create `src/utils/folder_scanner.py` - Scan folder and load all .txt files
4. Modify `src/ui/sidebar.py` - Replace file_uploader with Browse Folder button

**Expected User Experience:**
- Click "Browse Folder" → native folder picker opens at last used location
- Select folder → ALL .txt files auto-loaded instantly
- Next session: folder picker remembers location

**Detailed Plan:** See [plan file](C:\Users\Ang-Yu Lu\.claude\plans\resilient-tickling-gosling.md) for full technical specifications.

**Estimated Effort:** 2-3 hours

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

### Visualization & UX
- **Single-Page Accordion Workflow**: Streamlined sequential processing
- **Real-Time Previews**: See de-spiking and baseline effects before applying
- **Auto-Managed Plot Layers**: Visibility automatically adjusts per processing stage
- **Interactive Plotly Plots**: Publication-quality with zoom, pan, export
- **File Navigation**: Dropdown + Previous/Next buttons (recently fixed)
- **Batch Processing**: Load and process multiple files independently
- **Project Persistence**: Save/load full project state to JSON

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
- Upload .txt files in sidebar (two-column format: X, Y)
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
1. **Streamlit file uploader**: Cannot disable drag-and-drop UI, no path memory, manual file selection
2. **No recursive folder scan**: Users must manually select individual files
3. **Cloud deployment constraints**: Tkinter-based folder browser (planned) works only locally

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
- **[Plan: Local File Browser](C:\Users\Ang-Yu Lu\.claude\plans\resilient-tickling-gosling.md)**: Comprehensive plan for replacing file uploader (NOT YET IMPLEMENTED)

---

## Version History

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

**Last Updated:** 2025-12-28
**Version:** 2.2.1
**Status:** Production-ready with planned enhancements
