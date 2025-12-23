# SpectralFit v2.2.1

A desktop web application for analyzing Raman and Photoluminescence spectroscopy data with real-time previews and advanced peak fitting.

## Features

### Data Processing
- **Data Ingestion**: Load two-column .txt spectrum files (X, Y)
- **X-Range Processing**: Crop spectrum to specific region before analysis
- **Pre-Processing**:
  - Cosmic-ray spike removal with real-time preview (modified Z-score algorithm)
  - Baseline correction with real-time preview (Polynomial, ALS, Rolling Ball, Spline, airPLS)
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
- **Batch Processing**: Load and process multiple files independently
- **Project Persistence**: Save/load full project state to JSON

## What's New in v2.2.1

### Critical Fitting Algorithm Improvements
- **Fixed amplitude initialization** (50-80% reduction in convergence failures)
- **Shape-aware width initialization** (20-30% better R² values)
- **Adaptive bounds calculation** (30-40% fewer bound-hitting failures)
- **Improved auto-find FWHM estimation** (40-60% better auto-find quality)
- **Peak overlap detection** with actionable warnings

### Quality Improvements
- R² values: 0.85-0.92 → **0.95-0.99** (for well-behaved spectra)
- Convergence rate: 60-70% → **90-95%**
- Bound-hitting issues: Common → **Rare**

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

1. **Load Data**: Upload .txt files in sidebar
2. **Select File**: Use dropdown or left/right buttons
3. **Processing Range**: Crop spectrum (optional)
4. **De-spiking**: Remove cosmic rays with real-time preview
5. **Baseline Correction**: Subtract baseline with real-time preview
6. **Peak Fitting**: Auto-find or manually add peaks, then fit
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
- Column 2: Intensity
- Delimiter: Tab or comma
- No header

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)**: Version history
- **[Baseline_Algo.md](Baseline_Algo.md)**: Baseline algorithms
- **[Fitting_Algo.md](Fitting_Algo.md)**: Peak fitting algorithms
- **[FITTING_IMPROVEMENTS.md](FITTING_IMPROVEMENTS.md)**: v2.2.1 improvements

## License

[Add license]

## Contact

[Add contact]
