# SpectralFit v2.4.1 - Project Summary

**Last Updated:** 2026-02-03
**Status:** Fully Functional

---

## Overview

SpectralFit is a Streamlit-based web application for Raman and Photoluminescence (PL) spectrum analysis. It provides an end-to-end workflow: data loading, preprocessing (spike removal, baseline correction), multi-peak Voigt fitting, and result export.

---

## Application Layout

**Desktop:** Two-column layout (70% plot / 30% control panel)
**Mobile:** Vertical stack (controls above plot)

### Center Column (70%)
- **File navigation bar** - Previous/Next arrows, file selector dropdown, file counter
- **Unified multi-layer plot** - Interactive Plotly figure with toggleable layers
- **Fit results table** - Displayed below plot after fitting (Label, Center, ±, Amp, FWHM, R², χ²)

### Right Column (30%) - Control Panel
Seven accordion sections in workflow order:
1. **Processing Range** - X-min/X-max cropping
2. **De-spiking** - Modified Z-score spike removal with real-time preview
3. **Baseline Correction** - 5 algorithms with real-time preview and exclusion ranges
4. **Peak Fitting** - Editable peak table, auto-find, Voigt fit
5. **Export** - PNG, CSV, HTML, batch master CSV
6. **Reset to Raw** - Undo all processing
7. **View Options** - Toggle plot layer visibility

### Sidebar (collapsed by default)
- Mode toggle (Raman / PL)
- Material preset system (Excel-based)
- Folder browser for batch file loading
- Project save/load (JSON)

---

## Features

### Data Loading
- Folder browser with batch loading of all .txt files
- Auto-detect mode from filename patterns (RM*/PL*)
- Drag-and-drop file upload
- Project restore from JSON

### Preprocessing
- **X-Range Cropping** - Limit spectrum to region of interest
- **De-spiking** - Modified Z-score (MAD-based), threshold 3.0-30.0, real-time preview
- **Baseline Correction** - 5 algorithms:
  - Polynomial (degree 1-10)
  - ALS (Asymmetric Least Squares)
  - Rolling Ball (morphological)
  - Spline (piecewise cubic)
  - airPLS (adaptive iteratively reweighted)
- **Exclusion ranges** - Mask peak regions during baseline fitting (e.g., "1200-1400; 2600-2800")
- **Real-time previews** - See results before applying

### Peak Fitting
- Multi-peak Voigt profile fitting (lmfit, Levenberg-Marquardt)
- Editable peak table (label, center, amplitude, FWHM, shape, color)
- Auto-find peaks (scipy, configurable max peaks and prominence)
- Fit quality metrics: R², χ², convergence time
- Stale fit detection when preprocessing changes after fitting

### Material Preset System (v2.3.0)
- Excel-based preset files (one sheet per material-mode)
- Stores complete workflow config: baseline algorithm, parameters, peak templates
- Single-click auto-workflow execution per file
- Batch auto-workflow: process all loaded files at once (v2.4.0)

### Visualization
- Unified multi-layer plot with 8+ toggleable traces:
  - Raw, De-spiked, Baseline-corrected, Fit total, Components, Residuals, Previews
- Automatic layer visibility based on processing stage
- Interactive Plotly (zoom, pan, hover)
- Full-width rendering
- Residual subplot with separate y-axis

### Export
- **Master CSV** - All files, all peaks in one table
- **Single spectrum CSV** - X, Y_raw, Y_processed, Y_fit, residuals, components
- **PNG** - High-resolution static image
- **HTML** - Interactive standalone plot

### Project Persistence
- Save/load full session state as JSON
- Preserves all processing settings, fit results, and data arrays
- Backward compatible with v2.1+ project files

---

## File Structure

```
SpectralFit/
├── app.py                          # Main entry point
├── requirements.txt                # Python dependencies (auto-installed by start scripts)
├── start.bat                       # Windows launcher (creates venv, installs deps, runs app)
├── start.sh                        # macOS/Linux launcher
├── presets/material_presets.xlsx    # Example preset file
├── src/
│   ├── models/
│   │   ├── spectrum.py             # SpectrumFile, SpectrumData, ProcessingSettings
│   │   ├── peak.py                 # PeakDefinition, FittedPeak, FitResult
│   │   ├── preset.py               # MaterialPreset, PeakTemplate, PresetLibrary
│   │   └── project.py              # ProjectState, ProjectMetadata
│   ├── processing/
│   │   ├── parser.py               # File parsing and mode detection
│   │   ├── despiking.py            # Modified Z-score spike removal
│   │   ├── baseline.py             # 5 baseline algorithms + exclusion ranges
│   │   ├── fitting.py              # Multi-peak Voigt fitting
│   │   └── auto_workflow.py        # Automated pipeline execution
│   ├── visualization/
│   │   ├── unified_plot.py         # Main plot + file navigation + fit results
│   │   └── plotter.py              # Export plots (composite, preview)
│   ├── ui/
│   │   ├── sidebar.py              # Settings, presets, file loading, project I/O
│   │   ├── control_panel.py        # 7 accordion sections
│   │   ├── session_state.py        # State initialization
│   │   ├── preprocess_tab.py       # Legacy (preserved)
│   │   ├── fit_tab.py              # Legacy (preserved)
│   │   └── export_tab.py           # Legacy (preserved)
│   └── io/
│       ├── export.py               # CSV, PNG, HTML export
│       ├── project_io.py           # Project save/load
│       └── preset_parser.py        # Excel preset parsing
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v2.4.1 | 2026-02-03 | Full-width plots, fit results below plot, auto-install deps |
| v2.4.0 | 2025-12-25 | Batch auto-workflow, smart file navigation |
| v2.3.0 | 2025-12-24 | Material preset system, exclusion ranges |
| v2.2.3 | 2025-12-23 | Folder browser with batch loading |
| v2.2.2 | 2025-12-23 | Editable peak table with inline editing |
| v2.2.1 | 2025-12-23 | Critical fitting algorithm improvements |
| v2.2.0 | 2025-12-20 | Single-page accordion layout |
| v2.1.0 | 2025-12-19 | Real-time baseline preview, auto mode detection |
| v2.0.0 | 2025-12-18 | Initial release |

---

## Running the App

**Recommended:** Double-click `start.bat` (Windows) or run `./start.sh` (macOS/Linux).
This automatically creates a virtual environment, installs all dependencies, and launches the app.

**Manual:**
```bash
cd SpectralFit
pip install -r requirements.txt
streamlit run app.py
```

---

## Dependencies

- streamlit
- plotly
- pandas
- numpy
- scipy
- lmfit
- openpyxl (for preset parsing)
- kaleido (optional, for PNG export)
