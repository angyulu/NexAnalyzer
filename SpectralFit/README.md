# SpectralFit v2.7.0

A desktop web application for analyzing Raman and Photoluminescence spectroscopy data with real-time previews, advanced peak fitting, and material-preset-driven automation.

## Features

### Data Processing
- **Data Ingestion**: Multi-select native file picker for `.txt` spectrum files (X, Y; multi-Y supported)
- **X-Range Processing**: Crop spectrum to specific region before analysis
- **Pre-Processing**:
  - Cosmic-ray spike removal with real-time preview (modified Z-score algorithm)
  - Baseline correction with real-time preview (Polynomial, ALS, Rolling Ball, Spline, airPLS, or None)
- **Peak Fitting**: Multi-peak Voigt profile fitting with:
  - Auto-find peak detection
  - Shape-aware initialization (Gaussian/Lorentzian mixing)
  - Adaptive parameter bounds
  - Overlap detection with warnings
- **Material Presets**: Excel-driven, one-click auto-workflow across X-range → despike → baseline → fit

### Visualization & UX
- **Single-Page Accordion Workflow**: Streamlined sequential processing
- **Real-Time Previews**: See de-spiking and baseline effects before applying
- **Auto-Managed Plot Layers**: Visibility automatically adjusts per processing stage
- **Interactive Plotly Plots**: Publication-quality with zoom, pan, export
- **Batch Processing**: Load and process multiple files independently
- **Project Persistence**: Save/load full project state to JSON

## What's New in v2.7.0

### Save Master CSV to the Raw-Data Folder
- A **"Save Master CSV to folder"** button in the Export section opens a native Save-As dialog **pre-pointed at the folder your raw `.txt` data came from**, with an **editable filename**, and writes the master CSV straight there (the in-browser download button is kept as a fallback).

See [CHANGELOG.md](CHANGELOG.md) for full details.

## What's New in v2.6.0

### Delete All Files
- A **"Delete All Files"** button in the sidebar's "Loaded Files" section clears every loaded spectrum in one click, instead of removing them one at a time. It sits next to the existing "Remove File" button.

See [CHANGELOG.md](CHANGELOG.md) for full details.

## What's New in v2.5.0

### Multi-Select File Picker (replaces folder picker)
- **Browse Spectrum Files** button opens a native OS multi-select dialog filtered to `.txt` (with "All files" fallback).
- Pick any subset of files across one or more folders — no more "load every `.txt` in this folder, like it or not".
- Last picked directory is remembered as the next dialog's starting location.
- Cancel is a clean no-op; re-picking already-loaded files is skipped silently with a count.
- Multi-Y files continue to split into `name__1.txt`, `name__2.txt`, ... entries.

### Fit Results Table Reordering (PL mode)
- The "Raw" summary row (raw spectrum max intensity, position, FWHM at half-max) now appears at the **top** of the fit-results table instead of the bottom, both in the in-app table and in exported master CSV. Makes the raw vs. fit comparison easier to scan.

See [CHANGELOG.md](CHANGELOG.md) for full details.

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
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

### Workflow

1. **Load Data**: Click **Browse Spectrum Files** in the sidebar and pick one or more `.txt` files
2. **Select File**: Use dropdown or left/right buttons above the plot
3. **Processing Range**: Crop spectrum (optional)
4. **De-spiking**: Remove cosmic rays with real-time preview
5. **Baseline Correction**: Subtract baseline with real-time preview
6. **Peak Fitting**: Auto-find or manually add peaks, then fit (or use a material preset for one-click full pipeline)
7. **Export**: Save plots, fit results, or project

### Plot Layer Visibility

Automatically managed at each stage:
- **X-range**: Only "Raw" data
- **Despike**: "Raw" AND "De-spiked" (comparison)
- **Baseline**: "De-spiked" AND "Preview baseline" (red dashed)
- **Peak Fit**: "Corrected", "Fit Total", "Components"

Override manually in **View Options**.

## File Format

Two-column .txt files:
- Column 1: Wavenumber (cm⁻¹) or Wavelength (nm)
- Column 2+: Intensity (one column for standard files, multiple columns for multi-Y files)
- Delimiter: Tab, comma, or whitespace (auto-detected)
- No header

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)**: Install + step-by-step usage guide
- **[CHANGELOG.md](CHANGELOG.md)**: Version history
- **[Summary.md](Summary.md)**: Architecture and design overview
- **[Baseline_Algo.md](Baseline_Algo.md)**: Baseline algorithms
- **[Fitting_Algo.md](Fitting_Algo.md)**: Peak fitting algorithms
- **[FITTING_IMPROVEMENTS.md](FITTING_IMPROVEMENTS.md)**: v2.2.1 improvements

## License

[Add license]

## Contact

[Add contact]
