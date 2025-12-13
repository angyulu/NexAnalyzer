# Product Requirements Document: SpectralFit

**Raman & Photoluminescence (PL) Spectrum Analysis Tool**

**Version:** 2.0  
**Status:** Approved for Development  
**Date:** December 13, 2025  
**Target Platform:** Desktop Web App (Streamlit)

---

## Executive Summary

SpectralFit is a unified, open-source Python web application for analyzing Raman and Photoluminescence spectroscopy data. It streamlines a fragmented workflow by providing a **linear, single-spectrum processing pipeline**: data ingestion → cosmic-ray removal → baseline correction → multi-peak Voigt fitting → publication-quality visualization and export.

The tool is designed for researchers who understand their spectroscopy but want robust, reproducible, physics-aware analysis without juggling multiple software packages.

### Key Differentiators

- **Physics-aware modes:** Distinct handling for Raman (wavenumber, cm⁻¹) and PL (wavelength, nm) with automatic defaults and bounds.
- **Robust pre-processing:** Modified Z-score spike detection (inspired by standard chemometrics practices) and dual baseline correction (polynomial and Asymmetric Least Squares).
- **Smart fitting:** Voigt profiles with Levenberg–Marquardt least squares, constrained by mode-specific auto-bounds and optional auto-peak detection.
- **Visual precision:** Interactive Plotly plots with residuals, per-component visibility, and full styling control.
- **Simple export:** Master CSV with raw intensity values, PNG/HTML figures, and project state save/load.

---

## Product Goals and Non-Goals

### Goals

- Provide a **linear workflow** that mirrors standard spectroscopy practice: load spectrum → de-spike → baseline correct → fit peaks → export results.
- Support **Raman (cm⁻¹, including negative shifts)** and **PL (nm)** data with mode-aware defaults and fitting tolerances.
- Implement **robust baseline correction** using polynomial and Asymmetric Least Squares (ALS) algorithms, eliminating tedious manual baseline fitting.
- Use **Voigt profiles** with constrained nonlinear least-squares fitting (lmfit backend) for publication-quality multi-peak decomposition.
- Enable **precise visual inspection** via interactive plots showing data, total fit, individual component curves, and residuals.
- Support **batch file loading** so users can upload multiple files and process them serially with the same or different settings.
- Provide **simple, fast exports** (Master CSV + figures) suitable for further analysis and publication.

### Non-Goals (This Version)

- **No batch processing** across files (i.e., no "apply these settings to all 50 files at once").
- **No advanced noise models** (e.g., Poisson maximum likelihood, heteroscedastic weighting).
- **No global optimization** (Differential Evolution, simulated annealing) — local Levenberg–Marquardt is sufficient for good initial guesses.
- **No alternative line shapes** (Lorentzian-only, Gaussian-only, Asymmetric); Voigt profiles are standard and sufficient.
- **No metadata-rich or parametric exports** (e.g., per-peak covariances, fit diagnostics); CSV export is intentionally minimal and raw-value focused.
- **No automated mode detection** or spectroscopy metadata parsing from file headers.

---

## Target Users and Use Cases

### Primary Users

- **Raman spectroscopy researchers** analyzing carbon materials, nanostructures, semiconductors, or polymers.
- **Photoluminescence researchers** studying fluorescence or emission spectra.
- Lab researchers who collect spectra with commercial instruments and need to process them reproducibly and quickly.
- Users comfortable with peak positions, widths, and baseline concepts but want robust, repeatable computational support.

### Key Use Cases

1. **Cosmic-ray spike removal**  
   Remove single-point outliers (cosmic-ray hits, electrical spikes) from a raw spectrum using a robust modified Z-score method. Visual preview before applying.

2. **Background/baseline correction**  
   - For Raman: Remove fluorescence, Rayleigh scatter, or instrumental slope.
   - For PL: Remove fluorescence background or detector offset.
   - Choice between simple polynomial (1–10 degree) or adaptive ALS for complex backgrounds.

3. **Multi-peak decomposition**  
   Fit 2–10 overlapping peaks using Voigt profiles (mixed Gaussian/Lorentzian), with either manual center/width entry or auto-detection, and constrained by physics-aware bounds.

4. **Batch loading and inspection**  
   Upload 5–50 Raman/PL spectra from an instrument; switch between files to apply baseline and fitting; export combined results.

5. **Publication-ready figures**  
   Generate composite plots (data + fit + components + residuals) with custom styling (colors, line widths) for reports and papers.

---

## Data Model and Input Assumptions

### Input File Format

- **Type:** Plain text (`.txt`).
- **Delimiters:** Tab-delimited or comma-delimited (auto-detected or user-selectable).
- **Structure:** Exactly two numeric columns, **no headers**.
  - **Column 1:** X-axis (Raman shift in cm⁻¹ or PL wavelength in nm).
  - **Column 2:** Y-axis (intensity in raw detector units: counts, voltage, arbitrary units, etc.).
- **Line endings:** Windows (`\r\n`) or Unix (`\n`) both acceptable.
- **Special handling for Raman:** X-values **may be negative** (e.g., Stokes shift-corrected spectra from −680 to +500 cm⁻¹); negative values must be preserved and displayed as-is in plots and exports.
- **Example (Raman):**
  ```
  -680.924	495.667
  -679.927	492.000
  -678.930	500.000
  ```
- **Example (PL):**
  ```
  850.452	698.400
  850.607	707.600
  850.762	709.400
  ```

### File Handling

- **Batch upload:** Multi-file file picker (Streamlit `st.file_uploader`); users can upload 1–100 `.txt` files in one session.
- **File selector:** Dropdown listing uploaded filenames; selecting a file switches the entire app context (plot, baseline settings, fit table) to that file's state.
- **Per-file state:** Each file maintains its own processing history (de-spiked data, baseline settings, peak table, fit results) in memory for the session duration.
- **No automatic merging:** Files are processed independently; no stacking or concatenation.

---

## Functional Requirements

### Global Controls & Sidebar

#### FR-1: Mode Switching

**Requirement**  
A persistent radio button toggling between **Raman (cm⁻¹)** and **PL (nm)** modes.

**Behavior**
- Affects axis labels and units in all plots.
- Controls default fitting parameter bounds:
  - **Raman:** Center bounds = guessed center ± 5 cm⁻¹; typical FWHM range 1–100 cm⁻¹.
  - **PL:** Center bounds = guessed center ± 30 nm; typical FWHM range 5–200 nm.
- Influences default ALS parameters (optional in Phase 2 or later).

#### FR-2: Batch File Loading

**Requirement**  
Multi-file uploader and file selector dropdown.

**Behavior**
- Accept `.txt` files (tab or comma-delimited, 2 numeric columns, no headers).
- Parse files robustly (ignore non-numeric rows, handle scientific notation like `6.02E+02`).
- File selector dropdown lists all successfully loaded files.
- Clicking a filename switches the main app view (plot, baseline, fit table) to that file's state.
- Each file has its own independent processing pipeline; no cross-file coupling.

---

### Stage 1: De-Spiking and Baseline Correction

#### FR-3: Interactive De-Spiking (Cosmic Ray Removal)

**Algorithm**  
Modified Z-score on intensity values:

$$z_i = \frac{0.6745 \cdot (y_i - \text{median}(y))}{\text{MAD}(y)}$$

where MAD is the Median Absolute Deviation. Spikes are points with $|z_i| >$ threshold.

**UI Controls**
- **Slider:** Spike Sensitivity (Modified Z threshold)
  - Range: 3.0–15.0
  - Default: **6.0** (balanced for typical Raman/PL data)
  - Help text: "Lower = more aggressive spike removal. Higher = only extreme spikes."
- **Button:** `Auto Remove Spikes` — apply threshold and replace spike values with local median.
- **Button:** `Reset to Raw` — revert current file to original unmodified data.

**Behavior**
- Plot preview shows spike candidates (e.g., red dots) overlaid on data.
- User adjusts slider → plot updates in real-time.
- Once "Auto Remove Spikes" is clicked, de-spiked data becomes the input for baseline correction.
- Subsequent operations use de-spiked data; spike removal is not reversible within a fitting session (only via "Reset to Raw").

#### FR-4: Baseline Subtraction

**Algorithms Available**

1. **Polynomial Baseline**
   - User selects degree (1–10).
   - Fit $P(x) = a_0 + a_1 x + a_2 x^2 + \cdots + a_n x^n$ to entire spectrum using least squares.
   - Subtract $P(x)$ from data to obtain baseline-corrected Y.
   - **Recommended for:** Simple, smooth slopes (PL fluorescence, Raman with gentle backgrounds).

2. **Asymmetric Least Squares (ALS)**
   - Iteratively fit a smooth baseline with asymmetric weighting: peaks de-emphasized, baseline regions emphasized.
   - **Parameters:**
     - $\lambda$ (lambda): Smoothness penalty; typical range 10⁴–10⁵ (higher = stiffer baseline).
     - $p$ (asymmetry): Weight ratio; typical range 0.001–0.01 (lower = baseline hugs lower envelope).
   - **Recommended for:** Complex fluorescence, Raman with noise, or multi-feature backgrounds.

**UI Controls**
- **Dropdown:** Select algorithm = `Polynomial` / `ALS`.
- **Sliders/inputs:**
  - If Polynomial: degree (1–10).
  - If ALS: $\lambda$ and $p$ sliders with sensible defaults (e.g., λ = 10⁴, p = 0.001).
- **Checkbox:** `Show Baseline` — overlay calculated baseline on main plot.
- **Checkbox:** `Show Residuals` — show baseline fit residuals separately.

**Behavior**
- Calculate baseline from de-spiked data.
- Subtract to produce baseline-corrected Y in **raw units** (no normalization).
- Baseline-corrected data is passed to the fitting stage.
- Changing baseline algorithm or parameters updates the plot and resets any previous fit.

---

### Stage 2: Peak Model and Fitting

#### FR-5: Dynamic Peak Table

**UI Component**  
An editable table (`st.data_editor`) where each row represents one peak to be fitted.

**Columns**
- **Label** (optional text; no pre-defined suggestions; e.g., "D-Band", "Peak_1").
- **Center** (numeric; initial guess in cm⁻¹ or nm depending on mode).
- **Amplitude** (numeric; initial guess in **raw intensity units**, not normalized).
- **Width (FWHM)** (numeric; initial full-width-at-half-maximum guess in X-units).
- **Shape** (numeric 0–1; 0 = pure Gaussian, 1 = pure Lorentzian; or internal Voigt default).
- **Color** (optional hex string; used in plotting component curves).

**Behavior**
- User can add rows (insert new peak), remove rows (delete peak), and edit all fields.
- Table is fully editable; changes are reflected immediately in auto-bounds calculations (if visible).
- Per-file: Table state is saved per file; switching files recalls that file's peak table.

#### FR-5a: Auto-Find Peaks

**Algorithm**  
Automated peak detection using standard signal processing:

1. Apply peak-finding algorithm (e.g., `scipy.signal.find_peaks`) to baseline-corrected Y.
2. For each detected peak, estimate:
   - **Center:** Peak position (X value of maximum).
   - **Amplitude:** Y value at peak maximum.
   - **FWHM:** Width at half-maximum height.
3. Assign default shape factor (e.g., 0.5 for balanced Voigt).

**UI Controls**
- **Button:** `Auto-Find Peaks` — populate or append peaks to the peak table.
- **Optional sliders:**
  - Prominence threshold (fraction of max intensity).
  - Minimum distance between peaks (in points or X-units).

**Behavior**
- Clicking `Auto-Find Peaks` fills the table with detected peaks.
- User reviews, edits, removes as needed before fitting.
- Auto-detected values are initial guesses; fitting will refine them.

#### FR-6: Intelligent Constraints (Auto-Bounds)

**Center Bounds**  
When a peak's center is entered, automatically set fitting bounds:
- **Raman mode:** center − 5 cm⁻¹ to center + 5 cm⁻¹.
- **PL mode:** center − 30 nm to center + 30 nm.

These bounds prevent the fitter from drifting to nearby peaks or noise features.

**Width Bounds (Recommended)**
- **Min:** At least 2–3 spectral resolution steps (automatic from data spacing).
- **Max:** At most 50% of total spectral range.

Prevents zero-width or unreasonably broad peaks.

**Amplitude Bounds**
- **Min:** 0 (no negative amplitudes; unphysical for positive-definite spectra).
- **Max:** 1.5–2.0× maximum baseline-corrected intensity for that file.

Prevents amplitude from fitting noise or drifting very far from data.

**Advanced Mode**  
- Checkbox: `Advanced` (optional).
- If checked, reveal additional columns: `Center Min`, `Center Max`, `Width Min`, `Width Max`, `Amplitude Max`.
- Allow manual override of auto-calculated bounds.

#### FR-7: Fitting Execution and Error Handling

**Solver & Model**  
- **Backend:** `lmfit` (Python) with `VoigtModel` for each peak.
- **Algorithm:** Levenberg–Marquardt (L-M) nonlinear least-squares via scipy.optimize.
- **Model form:**
  $$y_{\text{fit}}(x) = \text{baseline} + \sum_{i=1}^{N_{\text{peaks}}} V_i(x; c_i, \sigma_i, \gamma_i, a_i)$$
  where $V_i$ is a Voigt profile for peak $i$.

**Controls**
- **Button:** `Run Fit` — execute lmfit with current peak table and bounds.
- **Status display:**
  - Before: "Ready to fit" or "Modify peak table above".
  - During: "Fitting in progress..." (with optional iteration counter).
  - After success: "Fit converged in X s. χ² = Y, R² = Z."
  - After failure: "Fit did not converge. Suggestions: (1) Check center guesses, (2) Widen bounds, (3) Reduce peak count."

**Behavior**
- Fit minimizes sum of squared residuals: $\chi^2 = \sum_j (y_j - \hat{y}_j)^2$.
- If convergence achieved: display fitted parameters (center, amplitude, width, shape) and quality metrics.
- If convergence fails: show friendly error message with actionable suggestions.
- Fitted results (parameters, chi-squared, R²) are cached for export and plotting.

---

### Stage 3: Visualization and Export

#### FR-8: Publication Plot

**Layout**
- **Top subplot (3/4 height):** Data (baseline-corrected, raw units) + total fitted curve + individual Voigt components (one line per peak).
- **Bottom subplot (1/4 height):** Residual plot (Data − Fit) vs X.

**Plot Features**
- **Interactivity:** Zoom, pan, hover info (value labels) via Plotly.
- **Component toggles:** Legend checkboxes to show/hide individual peaks and total fit.
- **Styling panel (collapsible):**
  - Per-peak color picker.
  - Line style options (solid, dashed, dotted).
  - Line width slider (0.5–5 pt).
  - Data point marker style (dots, crosses, none).

**Axis labels**
- X-axis: "Raman Shift (cm⁻¹)" or "Wavelength (nm)" depending on mode.
- Y-axis: "Intensity (a.u.)" or user-customizable label.

#### FR-9: Fit Quality Metrics

**Display**
- Show at least:
  - $\chi^2$ or reduced $\chi^2_r = \chi^2 / (\text{N} - \text{P})$ (sum of squared residuals, adjusted for degrees of freedom).
  - $R^2$ (coefficient of determination) = $1 - \frac{\text{SS}_{\text{res}}}{\text{SS}_{\text{tot}}}$.
- Location: Below the plot or in a collapsible "Fit Info" panel.
- Help text explaining what good/poor values mean.

#### FR-10: Export Functionality

**Master CSV Export**
- Single `.csv` file containing **all fitted peaks from all files in the current session**.
- Columns:
  - `filename` — source file name.
  - `mode` — Raman or PL.
  - `peak_label` — user-supplied label.
  - `center` — fitted peak center (cm⁻¹ or nm).
  - `amplitude` — fitted amplitude in **raw units**.
  - `FWHM` — fitted full-width-at-half-maximum (cm⁻¹ or nm).
  - `shape` — mixing factor (0=Gaussian, 1=Lorentzian).
  - `chi2` or `R2` — optional fit quality per spectrum.
- **Values:** All in raw (non-normalized) units from original data.
- **Delimiter:** Comma-separated (standard CSV).
- No extra metadata (algorithm names, user notes, timestamps) unless explicitly added later.

**Figure Export**
- **PNG:** Static image of current composite plot (data + fit + components + residuals).
- **HTML (optional):** Interactive Plotly figure (full zoom, pan, legend interactivity).

**File naming**
- CSV: `spectralfit_export_{timestamp}.csv` or user-customizable.
- Figures: `spectralfit_plot_{filename}_{timestamp}.png/html` or similar.

#### FR-11: Project Save and Load

**Save Functionality**
- **Button:** `Save Project` → downloads `project_state.json`.
- **Content:**
  - Version and date.
  - Per-file settings:
    - Mode (Raman/PL).
    - De-spike threshold.
    - Baseline algorithm and parameters (degree, λ, p).
  - Peak table (all columns) for each file.
  - Styling preferences (colors, line widths).
  - **Optional:** Actual spectral data (to make project self-contained) or just file references (user re-loads `.txt` files).

**Load Functionality**
- **Button:** `Load Project` → file picker for `.json`.
- **Behavior:** Restores all settings, peak tables, and styling for files present in the project.
  - If a `.txt` file referenced in the project is not yet uploaded, show a warning and skip that file.
  - Allow user to re-upload missing `.txt` files and reload the project to populate them.

**JSON Schema** (simplified example)
```json
{
  "version": "2.0",
  "timestamp": "2025-12-13T22:00:00Z",
  "files": [
    {
      "filename": "sample_raman.txt",
      "mode": "Raman",
      "de_spike_threshold": 6.0,
      "baseline": {
        "algorithm": "ALS",
        "lambda": 10000,
        "p": 0.001
      },
      "peaks": [
        {
          "label": "D-Band",
          "center": 1350.5,
          "amplitude": 150.0,
          "width": 50.0,
          "shape": 0.5,
          "color": "#FF0000"
        }
      ]
    }
  ]
}
```

---

## Non-Functional Requirements

### Performance

- Single-spectrum operations (de-spike, baseline, fit) should complete in **1–3 seconds** on typical lab laptops (modern CPU, 8+ GB RAM) for spectra with 10³–10⁴ points.
- Plotting and re-rendering should be smooth (< 500 ms) when toggling components or adjusting styling.

### Robustness

- **File parsing:** Handle malformed lines gracefully (skip non-numeric rows, warn user).
- **Error messages:** Clear, actionable feedback for common issues (e.g., file format errors, fitting non-convergence, missing columns).
- **State recovery:** If an operation fails (e.g., baseline fitting for a pathological spectrum), show error but allow user to try different settings without reloading file.

### Usability

- **Default settings should "just work"** for typical Raman/PL spectra with minimal tuning:
  - Spike sensitivity threshold: 6.0 (conservative, works for most data).
  - Baseline: Polynomial degree 1–3 as starting point.
  - ALS (if chosen): λ ~ 10⁴, p ~ 0.001 as defaults.
  - Mode-aware center bounds automatically applied.
  - Auto-find peaks should correctly identify 2–5 prominent features without user tweaking.

### Accessibility

- Tooltips and help text for all controls explaining parameters, their ranges, and physical meaning.
- Support for standard keyboard navigation (Tab, Enter, Escape).
- Responsive design for 1024×768 and larger screen resolutions.

---

## User Interface Layout

### Sidebar (Fixed, Left Panel)

1. **Header / Logo**
   - "SpectralFit" title and optional logo/icon.

2. **Mode Toggle**
   - Radio buttons: `( ) Raman (cm⁻¹)` | `( ) PL (nm)`
   - Default: Raman.

3. **File Upload & Selection**
   - File uploader: "Upload .txt files (up to 100 files)".
   - File selector dropdown: "Current file: [filename]".
   - Status: "Loaded N files" or "No files loaded".

4. **Project I/O**
   - Button: `Save Project` (downloads JSON).
   - Button: `Load Project` (file picker for JSON).

---

### Main Area (Right Panel)

A Streamlit `st.tabs()` container with three tabs:

#### **Tab 1: Pre-process**

- **Top:** Large Plotly chart showing raw data, de-spiked points highlighted.
- **Section 1 – De-spiking:**
  - Slider: "Spike Sensitivity (Modified Z threshold)" [3.0–15.0, default 6.0].
  - Button: `Auto Remove Spikes`.
  - Button: `Reset to Raw`.
  - Status: "N spikes detected / removed" or "No spikes found".

- **Section 2 – Baseline Subtraction:**
  - Dropdown: "Baseline Algorithm" [`Polynomial` | `ALS`].
  - If Polynomial:
    - Slider: "Degree" [1–10, default 2].
  - If ALS:
    - Slider: "Lambda (smoothness)" [1e3–1e6, default 1e4].
    - Slider: "p (asymmetry)" [0.001–0.1, default 0.001].
  - Checkbox: `Show Baseline` (overlay on plot).
  - Checkbox: `Show Residuals` (separate subplot).

#### **Tab 2: Fit Model**

- **Top:** Editable data_editor table with peak definitions.
  - Columns: Label, Center, Amplitude, Width (FWHM), Shape, Color.
  - User can add/remove/edit rows.

- **Controls above table:**
  - Button: `Auto-Find Peaks` (populate table).
  - Checkbox: `Advanced` (reveal min/max bound columns).

- **Central:** Large primary button `RUN FIT`.

- **Below:** Status bar
  - "Ready to fit" or "Fit converged in X s. χ² = Y, R² = Z" or "Fit failed: ...".

#### **Tab 3: Visualize & Export**

- **Top:** Composite plot
  - Top subplot (3/4): Data + fit + components + residuals.
  - Bottom subplot (1/4): Residuals vs X.
  - Legend with component visibility toggles.

- **Right-side collapsible panel: "Styling"**
  - Per-peak color, line style, line width.
  - Data point marker style.
  - Save current styling (embed in project state).

- **Below plot:** Fit metrics
  - χ², R², and brief interpretation.

- **Bottom: Export Zone**
  - Button: `Download CSV` (Master CSV with all peaks, all files).
  - Button: `Download PNG` (current plot).
  - Button: `Download HTML` (interactive Plotly figure).

---

## Development Roadmap

### Phase 1: Foundation (Week 1–2)

**Deliverables**
- Streamlit app scaffold with sidebar and three-tab layout.
- File uploader and file selector dropdown (in-memory storage).
- Raw data parsing (tab/comma-delimited, two columns, no headers).
- Mode toggle (Raman/PL) and persistent state.
- Basic Plotly scatter plot of raw data per file.

**Definition of Done**
- User can upload 3–5 `.txt` files; app displays them; switching files updates the plot.

### Phase 2: Cleaning (Week 3–4)

**Deliverables**
- Modified Z-score de-spiking algorithm with slider and preview.
- Polynomial baseline subtraction (degree 1–10).
- Basic ALS baseline subtraction (λ and p sliders).
- Baseline visualization overlay and residual subplot.
- Per-file state persistence (de-spike settings, baseline params).

**Definition of Done**
- User can de-spike a spectrum, view results, and undo. Baseline can be corrected with either algorithm and previewed.

### Phase 3: Fitting Engine (Week 5–7)

**Deliverables**
- Peak table UI (editable data_editor).
- Auto-find peaks algorithm and button.
- Voigt profile model (lmfit VoigtModel).
- Levenberg–Marquardt fitting with lmfit backend.
- Auto-bounds logic (mode-aware center, adaptive width/amplitude).
- Convergence messaging and error handling.
- Fit quality metrics (χ², R²).

**Definition of Done**
- User can manually or auto-populate peaks, adjust guesses, run fit, and see results. Fit converges on typical 2–3 peak Raman/PL spectra in < 2 seconds.

### Phase 4: Visualization & Export (Week 8–9)

**Deliverables**
- Composite plot (data + fit + components + residuals) with Plotly.
- Per-component visibility toggles (legend checkboxes).
- Styling panel (color, line style, line width per peak).
- Master CSV export (all peaks, all files, raw units).
- PNG and HTML figure export.

**Definition of Done**
- User can style a fit plot and export it as a publication-ready PNG. CSV contains all fitted results across all loaded files.

### Phase 5: Polish & Enhancements (Week 10–11)

**Deliverables**
- Project save/load (JSON with state and optional spectral data).
- ALS preset profiles per mode (optional; can defer if time-limited).
- Advanced bounds editing (checkboxes to reveal min/max columns).
- Tooltips and help text across all controls.
- UI/UX refinements (responsive layout, loading spinners, better error messages).
- Comprehensive testing (edge cases: single-peak spectra, very noisy data, pathological baselines).

**Definition of Done**
- User can save and reload a project; preset ALS parameters are available; app handles edge cases gracefully.

### Phase 6: Release Candidate (Week 12)

**Deliverables**
- Final testing and bug fixes.
- Documentation (README, user guide, example workflows).
- Code cleanup and inline comments.
- Optional: Docker/conda environment file for easy setup.

---

## Algorithm Details (for Developers)

### De-Spiking: Modified Z-Score

```python
def remove_spikes(y, threshold=6.0):
    """
    Remove spikes using modified Z-score based on MAD.
    
    Args:
        y (array): Intensity values.
        threshold (float): Z-score threshold.
    
    Returns:
        y_clean (array): Cleaned intensities (spikes replaced by median of neighbors).
    """
    median_y = np.median(y)
    mad = np.median(np.abs(y - median_y))
    
    z_scores = 0.6745 * (y - median_y) / (mad + 1e-10)
    spike_mask = np.abs(z_scores) > threshold
    
    y_clean = y.copy()
    for idx in np.where(spike_mask)[0]:
        # Replace spike with median of ±2 neighbors
        neighbors = y[[max(0, idx-2):min(len(y), idx+3)]]
        y_clean[idx] = np.median(neighbors)
    
    return y_clean, spike_mask
```

### Baseline Subtraction

#### Polynomial

```python
from scipy.polynomial import Polynomial

def baseline_polynomial(x, y, degree=2):
    """Fit and subtract polynomial baseline."""
    p = Polynomial.fit(x, y, degree)
    baseline = p(x)
    y_corrected = y - baseline
    return y_corrected, baseline
```

#### Asymmetric Least Squares (ALS)

```python
from scipy.linalg import solve_banded

def baseline_als(y, lam=1e4, p=0.001, niter=10):
    """
    Asymmetric Least Squares baseline correction.
    
    Args:
        y (array): Intensity values.
        lam (float): Smoothness parameter.
        p (float): Asymmetry parameter (lower = baseline hugs bottom).
        niter (int): Number of iterations.
    
    Returns:
        baseline (array): Fitted baseline.
        y_corrected (array): Baseline-corrected data.
    """
    N = len(y)
    # Second difference matrix
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(N-2, N), format='csr')
    w = np.ones(N)
    
    for _ in range(niter):
        W = sparse.diags(w)
        Z = W + lam * D.T @ D
        z = solve(Z.tocsr(), W @ y)
        w = p * (y > z) + (1 - p) * (y <= z)
    
    return z, y - z
```

### Voigt Fitting with lmfit

```python
from lmfit.models import VoigtModel
from lmfit import Model, Parameters

def fit_voigt_peaks(x, y, peaks_df):
    """
    Fit multiple Voigt peaks to baseline-corrected data.
    
    Args:
        x (array): X-axis (cm^-1 or nm).
        y (array): Baseline-corrected intensity.
        peaks_df (DataFrame): Columns [center, amplitude, width, shape, ...]
    
    Returns:
        result: lmfit MinimizerResult with fitted parameters.
    """
    model = None
    params = Parameters()
    
    for idx, row in peaks_df.iterrows():
        voigt = VoigtModel(prefix=f'p{idx}_')
        if model is None:
            model = voigt
        else:
            model += voigt
        
        # Add parameters
        params.add(f'p{idx}_center', value=row['center'], 
                   min=row.get('center_min'), max=row.get('center_max'))
        params.add(f'p{idx}_amplitude', value=row['amplitude'],
                   min=0, max=row.get('amplitude_max', 2*y.max()))
        params.add(f'p{idx}_sigma', value=row['width']/3.6,  # Rough conversion FWHM->sigma
                   min=0.01)
        params.add(f'p{idx}_gamma', value=row['width']/3.6,
                   min=0.01)
        params.add(f'p{idx}_fraction', value=row.get('shape', 0.5),
                   min=0, max=1)
    
    result = model.fit(y, params, x=x, method='leastsq')
    return result
```

---

## References & Standards

- **Modified Z-score (MAD-based):** Iglewicz & Hoaglin (1993); standard in chemometrics and spectroscopy preprocessing.
- **Asymmetric Least Squares (ALS):** Eilers & Boelens (2005); widely used in Raman baseline correction.
- **Voigt Profile:** NIST Special Publication 330; standard line shape for spectroscopy.
- **lmfit:** Newville et al.; Python nonlinear least-squares fitting library.
- **Streamlit:** Popular lightweight web framework for data apps.
- **Plotly:** Interactive plotting library for web-based visualization.

---

## Appendix: Example Workflow

1. **User launches SpectralFit.**
2. **Uploads** 3 Raman spectra (`.txt` files with wavenumber and intensity).
3. **Selects** "Raman (cm⁻¹)" mode.
4. **Switches to first file** via dropdown.
5. **De-spiking:**
   - Adjusts slider to 6.0.
   - Clicks `Auto Remove Spikes`; 2 cosmic rays detected and replaced.
6. **Baseline:**
   - Selects ALS; sets λ=10⁴, p=0.001.
   - Checks `Show Baseline`; visually confirms baseline fit.
7. **Fitting:**
   - Clicks `Auto-Find Peaks`; app detects 3 peaks (D-band, G-band, 2D-band).
   - Reviews and adjusts center guesses by ±10 cm⁻¹.
   - Clicks `RUN FIT`; fit converges in 1.2 seconds with R²=0.998.
8. **Styling:**
   - Changes peak colors to RGB (red, green, blue).
   - Sets line widths (2 pt for data, 1.5 pt for fit).
9. **Export:**
   - Downloads PNG of styled plot.
   - Downloads Master CSV containing all 3 spectra's fitted peaks.
10. **Repeats steps 4–9 for remaining files.**
11. **Saves project** for later refinement.

---

**Document Status:** Ready for Development  
**Next Step:** Code architecture review and Phase 1 sprint planning.
