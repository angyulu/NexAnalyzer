# Project Context

## Purpose
SpectralFit is a unified, open-source Python web application for analyzing Raman and Photoluminescence (PL) spectroscopy data. It provides a linear, single-spectrum processing pipeline: data ingestion → cosmic-ray removal → baseline correction → multi-peak Voigt fitting → publication-quality visualization and export.

**Target Users:** Research scientists and lab technicians analyzing Raman/PL spectra who need robust, reproducible, physics-aware analysis without juggling multiple software packages.

## Tech Stack
- **Language:** Python 3.9+
- **Web Framework:** Streamlit (desktop web app)
- **Scientific Computing:** NumPy, SciPy
- **Fitting Engine:** lmfit (Levenberg–Marquardt nonlinear least-squares)
- **Visualization:** Plotly (interactive plots)
- **Data Processing:** Pandas
- **Baseline Algorithms:** Polynomial fitting, Asymmetric Least Squares (ALS)

## Project Conventions

### Code Style
- **PEP 8 compliance:** Follow Python's official style guide
- **Naming conventions:**
  - Functions: `snake_case` (e.g., `remove_spikes`, `baseline_als`)
  - Classes: `PascalCase` (if needed)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_SPIKE_THRESHOLD = 6.0`)
  - Variables: `snake_case`
- **Docstrings:** Google-style docstrings for all public functions
- **Type hints:** Use where appropriate, especially for function signatures
- **Line length:** Max 100 characters (slightly relaxed from PEP 8's 79 for scientific code)

### Architecture Patterns
- **Single-page app structure:** Streamlit tabs for workflow stages (Pre-process → Fit Model → Visualize & Export)
- **Session state management:** Use `st.session_state` for per-file processing state
- **Separation of concerns:**
  - **UI layer:** Streamlit widgets and layout (in main app file)
  - **Processing layer:** Pure functions for algorithms (de-spiking, baseline, fitting)
  - **Data layer:** File I/O and parsing utilities
- **Functional programming:** Prefer pure functions that return new data rather than mutating state
- **Physics-aware modes:** Global mode toggle (Raman vs PL) controls units, bounds, and defaults throughout the pipeline

### Testing Strategy
- **Unit tests:** For core algorithms (de-spiking, baseline subtraction, fitting)
- **Test fixtures:** Sample Raman and PL spectra with known properties
- **Edge cases:**
  - Single-peak spectra
  - Very noisy data
  - Pathological baselines
  - Negative wavenumber values (Raman Stokes shifts)
- **Test framework:** pytest
- **Coverage target:** >80% for algorithmic functions
- **Integration testing:** Manual QA for UI workflows (streamlit is harder to test automatically)

### Git Workflow
- **Branching strategy:**
  - `main`: Production-ready code
  - `develop` (optional): Integration branch for features
  - Feature branches: `XXX-feature-name` (e.g., `001-spectralfit`, `002-als-baseline`)
- **Commit conventions:**
  - Imperative mood: "Add ALS baseline" not "Added ALS baseline"
  - Reference issues/specs when relevant
- **Pull requests:** Required for merging to `main`; include tests and documentation updates

## Domain Context

### Spectroscopy Fundamentals
- **Raman spectroscopy:** Measures vibrational modes via inelastic light scattering
  - X-axis: Raman shift (cm⁻¹), can include negative values for Stokes shifts
  - Common features: D-band (~1350 cm⁻¹), G-band (~1580 cm⁻¹) in carbon materials
- **Photoluminescence (PL):** Measures light emission after optical excitation
  - X-axis: Wavelength (nm), always positive
  - Broader peaks, often with fluorescence backgrounds

### Common Data Artifacts
- **Cosmic rays:** Single-point intensity spikes from radiation hits (CCD detectors)
- **Fluorescence backgrounds:** Slowly varying baseline underlying Raman peaks
- **Peak overlap:** Multiple Voigt profiles (Gaussian + Lorentzian convolution) sum to observed spectrum

### Voigt Profile
Standard line shape for spectroscopy; mixture of Gaussian (instrumental broadening) and Lorentzian (lifetime broadening). Controlled by:
- **Center:** Peak position (cm⁻¹ or nm)
- **Amplitude:** Peak height (raw detector units)
- **FWHM:** Full-width-at-half-maximum
- **Shape factor:** 0 = pure Gaussian, 1 = pure Lorentzian

## Important Constraints
- **No normalization:** All intensity values remain in raw detector units (counts, voltage, a.u.); never normalize to 0–1 or standardize
- **Single-spectrum processing:** No batch processing across files; each file processed independently
- **Raw value exports:** CSV exports must contain raw fitted values, not derived/normalized metrics
- **Negative wavenumbers:** Must preserve and correctly handle negative Raman shift values
- **Performance target:** Fit convergence in 1–3 seconds for typical spectra (10³–10⁴ points, 2–10 peaks)

## External Dependencies
- None (fully self-contained Python application)
- **File format:** Plain text `.txt` files (tab or comma-delimited, 2 numeric columns, no headers)
- **Deployment:** Local Streamlit server; no external APIs or cloud services required
