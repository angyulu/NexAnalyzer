# Data Model: SpectralFit

**Date**: 2025-12-13
**Phase**: 1 (Design & Contracts)
**Prerequisites**: spec.md, research.md

## Overview

This document defines the core data entities for SpectralFit. All entities are implemented as Python classes with validation logic. State is managed in Streamlit `session_state` during runtime and serialized to JSON for project persistence.

---

## Entity Diagram

```
ProjectState
  ├── version: str
  ├── timestamp: datetime
  ├── global_styling: StylingPreferences
  └── files: List[SpectrumFile]
        ├── filename: str
        ├── mode: Mode (enum: Raman | PL)
        ├── raw_data: SpectrumData
        ├── processed_data: SpectrumData
        ├── processing_settings: ProcessingSettings
        ├── peak_table: List[PeakDefinition]
        └── fit_result: FitResult | None

Relationships:
- ProjectState 1:N SpectrumFile
- SpectrumFile 1:1 ProcessingSettings
- SpectrumFile 1:N PeakDefinition
- SpectrumFile 0:1 FitResult (null if not fitted)
- FitResult 1:N FittedPeak (one per PeakDefinition)
```

---

## Core Entities

### 1. SpectrumFile

Represents a single uploaded .txt spectrum with all associated processing state.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `filename` | str | Non-empty, unique within session | Original .txt filename (e.g., "sample_raman.txt") |
| `mode` | Mode enum | "Raman" \| "PL" | Spectroscopy mode (affects units, bounds) |
| `raw_data` | SpectrumData | X and Y same length, Y > 0 | Original unmodified X, Y arrays |
| `processed_data` | SpectrumData | Derived from raw_data | Current state (post-despike, post-baseline) |
| `processing_settings` | ProcessingSettings | - | De-spike + baseline configuration |
| `peak_table` | List[PeakDefinition] | 0-10 peaks | User-defined peaks to fit |
| `fit_result` | FitResult \| None | Null until fitting succeeds | Fitted parameters and quality metrics |

**State Transitions**:

```
Raw → De-spiked → Baseline-corrected → Fitted → Exported
  ↑                                                 ↓
  └─────────────── Reset to Raw ───────────────────┘
```

**Validation Rules**:
- FR-001: `raw_data.X` and `raw_data.Y` must have exactly matching lengths.
- FR-003: `raw_data.X` may contain negative values (Raman mode).
- FR-007: Each file maintains independent state (no cross-file references).

**Derived Fields**:
- `despike_applied`: bool (True if `processed_data.Y !=

 raw_data.Y`)
- `baseline_applied`: bool (True if `processing_settings.baseline_algorithm` set)
- `is_fitted`: bool (True if `fit_result` is not None)

---

### 2. SpectrumData

Immutable container for X (wavelength/wavenumber) and Y (intensity) arrays.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `X` | np.ndarray (float64) | 1D, monotonic increasing/decreasing, length 100-100k | Wavenumber (cm⁻¹) or wavelength (nm) |
| `Y` | np.ndarray (float64) | 1D, same length as X, non-negative | Intensity in raw detector units |

**Validation Rules**:
- FR-003: X values may be negative (Raman Stokes shifts).
- Edge Case: Reject if Y is all zeros or constant ("Spectrum appears flat").
- FR-004: If original file had non-numeric rows, they're already skipped during parsing.

**Methods**:
- `get_spectral_resolution()`: Returns median(diff(X)) (used for auto-width bounds).
- `to_dict()`: Serialize to JSON-compatible dict `{"X": X.tolist(), "Y": Y.tolist()}`.
- `from_dict(d)`: Deserialize from dict.

---

### 3. ProcessingSettings

Configuration for de-spiking and baseline correction.

**Attributes**:

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `despike_threshold` | float | 6.0 | 3.0-15.0 | Modified Z-score threshold (FR-012) |
| `despike_applied` | bool | False | - | Whether spike removal has been run |
| `baseline_algorithm` | str | "Polynomial" | "Polynomial" \| "ALS" | Baseline correction method (FR-019) |
| `baseline_degree` | int | 3 | 1-10 | Polynomial degree (if algorithm = "Polynomial") |
| `baseline_lambda` | float | 10000.0 | 1e3-1e6 | ALS smoothness parameter (if algorithm = "ALS") |
| `baseline_p` | float | 0.001 | 0.001-0.1 | ALS asymmetry parameter (if algorithm = "ALS") |
| `baseline_applied` | bool | False | - | Whether baseline correction has been run |

**Validation Rules**:
- FR-012, FR-017, FR-018: Parameter ranges enforced by Streamlit sliders.
- If `baseline_algorithm == "Polynomial"`, ignore `baseline_lambda` and `baseline_p`.
- If `baseline_algorithm == "ALS"`, ignore `baseline_degree`.

---

### 4. PeakDefinition

User-defined initial guess for a single peak to be fitted.

**Attributes**:

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `label` | str | "" | Optional, max 50 chars | User-defined label (e.g., "D-Band") |
| `center` | float | Required | Within X range | Peak center position (cm⁻¹ or nm) |
| `amplitude` | float | Required | > 0 | Initial amplitude guess (raw units) |
| `width_fwhm` | float | Required | > 0 | Full-width-at-half-maximum (cm⁻¹ or nm) |
| `shape` | float | 0.5 | 0.0-1.0 | Voigt mixing (0=Gaussian, 1=Lorentzian) |
| `color` | str | "#1f77b4" | Valid hex color | Plot color for this peak component |
| `center_min` | float | Auto | < center | Lower bound for fitting (FR-029) |
| `center_max` | float | Auto | > center | Upper bound for fitting (FR-029) |
| `width_min` | float | Auto | > 0 | Minimum FWHM (2-3 spectral steps) |
| `width_max` | float | Auto | < 0.5×X range | Maximum FWHM (50% of range) |
| `amplitude_max` | float | Auto | > amplitude | Max amplitude (1.5-2.0× max(Y)) |

**Auto-Bounds Calculation** (FR-029):
- Raman mode: `center_min = center - 5`, `center_max = center + 5` (cm⁻¹)
- PL mode: `center_min = center - 30`, `center_max = center + 30` (nm)
- Width bounds: `width_min = 2 × spectral_resolution`, `width_max = 0.5 × (max(X) - min(X))`
- Amplitude bounds: `amplitude_max = 2.0 × max(Y_baseline_corrected)`

**Validation Rules**:
- FR-026: User can add/remove/edit rows.
- Edge Case: Warn if two peaks have centers within 2× FWHM ("Peaks may overlap excessively").

---

### 5. FitResult

Outcome of fitting the peak table to baseline-corrected data.

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if L-M solver converged (FR-034) |
| `fitted_peaks` | List[FittedPeak] | One entry per PeakDefinition |
| `total_fit_curve` | np.ndarray | Sum of all fitted peaks (same length as X) |
| `residuals` | np.ndarray | `Y_data - total_fit_curve` |
| `chi_squared` | float | Sum of squared residuals (FR-036) |
| `r_squared` | float | Coefficient of determination (FR-036) |
| `convergence_time` | float | Time in seconds (for FR-034 status message) |
| `error_message` | str | Empty if success, else actionable suggestion (FR-035) |

**Validation Rules**:
- SC-004: 90% of fits should achieve `r_squared > 0.95`.
- FR-035: If `success == False`, populate `error_message` with suggestions from pre-defined list:
  - "Fit did not converge. Suggestions: (1) Check center guesses, (2) Widen bounds, (3) Reduce peak count."

---

### 6. FittedPeak

Fitted parameters for a single peak (result of Voigt profile fit).

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `label` | str | Copied from PeakDefinition |
| `center` | float | Fitted peak center (cm⁻¹ or nm) |
| `center_stderr` | float | Standard error in center (from lmfit covariance) |
| `amplitude` | float | Fitted amplitude (raw units) |
| `amplitude_stderr` | float | Standard error in amplitude |
| `width_fwhm` | float | Fitted FWHM (cm⁻¹ or nm) |
| `width_stderr` | float | Standard error in FWHM |
| `shape` | float | Fitted Voigt mixing (0-1) |
| `component_curve` | np.ndarray | This peak's contribution to total fit |

**Export Mapping** (FR-046):
- CSV columns: `filename, mode, peak_label, center, amplitude, FWHM, shape, chi2, R2`
- One row per FittedPeak, duplicating chi2/R2 for each peak in same spectrum.

---

### 7. ProjectState

Top-level container for entire session (all files, settings, results).

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `version` | str | Schema version (e.g., "1.0.0") for forward compatibility (FR-055) |
| `timestamp` | str (ISO 8601) | Project save time (e.g., "2025-12-13T14:30:00Z") |
| `files` | List[SpectrumFile] | All loaded files with their state |
| `global_styling` | StylingPreferences | Default colors, line styles, widths |

**Serialization** (FR-051, FR-052):
- Convert all `np.ndarray` → `list` (JSON-compatible).
- Optionally exclude `raw_data` and `processed_data` arrays to reduce file size (user checkbox).
- If arrays excluded, `files[].raw_data` and `files[].processed_data` set to `null` in JSON.
- On load (FR-053, FR-054): If arrays are null, warn user to re-upload .txt files.

**JSON Schema** (see contracts/project-state-schema.json):
```json
{
  "version": "1.0.0",
  "timestamp": "2025-12-13T14:30:00Z",
  "files": [
    {
      "filename": "sample_raman.txt",
      "mode": "Raman",
      "raw_data": {"X": [...], "Y": [...]},
      "processed_data": {"X": [...], "Y": [...]},
      "processing_settings": {...},
      "peak_table": [{...}],
      "fit_result": {...}
    }
  ],
  "global_styling": {...}
}
```

---

### 8. StylingPreferences

Global and per-peak styling for plots.

**Attributes**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data_color` | str | "#1f77b4" | Color for raw/baseline-corrected data scatter |
| `data_line_width` | float | 2.0 | Line width in points (FR-043) |
| `data_marker_style` | str | "markers" | "markers" \| "lines" \| "markers+lines" |
| `fit_color` | str | "#ff7f0e" | Color for total fit curve |
| `fit_line_width` | float | 2.5 | Line width for total fit |
| `fit_line_style` | str | "solid" | "solid" \| "dash" \| "dot" |
| `residual_color` | str | "#d62728" | Color for residual subplot |
| `peak_colors` | List[str] | Plotly default palette | Colors for individual component curves |

**Validation Rules**:
- FR-043: Line width range 0.5-5.0 pt.
- Colors must be valid hex strings or Plotly named colors.

---

## State Lifecycle Example

**Scenario**: User loads `sample_raman.txt`, removes spikes, corrects baseline, fits 2 peaks.

1. **File Upload** (FR-001 to FR-007):
   ```python
   spectrum_file = SpectrumFile(
       filename="sample_raman.txt",
       mode="Raman",
       raw_data=SpectrumData(X=x_raw, Y=y_raw),
       processed_data=SpectrumData(X=x_raw, Y=y_raw),  # Initially identical
       processing_settings=ProcessingSettings(),
       peak_table=[],
       fit_result=None
   )
   st.session_state['files']['sample_raman.txt'] = spectrum_file
   ```

2. **De-spike** (FR-011 to FR-016):
   ```python
   settings = spectrum_file.processing_settings
   settings.despike_threshold = 6.0
   y_despike = remove_spikes(y_raw, threshold=6.0)
   spectrum_file.processed_data = SpectrumData(X=x_raw, Y=y_despike)
   settings.despike_applied = True
   ```

3. **Baseline Correction** (FR-017 to FR-024):
   ```python
   settings.baseline_algorithm = "Polynomial"
   settings.baseline_degree = 3
   y_baseline = subtract_polynomial_baseline(x_raw, y_despike, degree=3)
   spectrum_file.processed_data = SpectrumData(X=x_raw, Y=y_baseline)
   settings.baseline_applied = True
   ```

4. **Peak Table Entry** (FR-025 to FR-030):
   ```python
   peak1 = PeakDefinition(
       label="D-Band", center=1350, amplitude=500, width_fwhm=50,
       center_min=1345, center_max=1355  # Auto-calculated from mode
   )
   peak2 = PeakDefinition(
       label="G-Band", center=1580, amplitude=800, width_fwhm=40,
       center_min=1575, center_max=1585
   )
   spectrum_file.peak_table = [peak1, peak2]
   ```

5. **Fitting** (FR-031 to FR-037):
   ```python
   fit_result = fit_voigt_peaks(x_raw, y_baseline, spectrum_file.peak_table)
   if fit_result.success:
       spectrum_file.fit_result = FitResult(
           success=True,
           fitted_peaks=[FittedPeak(...), FittedPeak(...)],
           total_fit_curve=...,
           residuals=y_baseline - total_fit_curve,
           chi_squared=12.5,
           r_squared=0.987,
           convergence_time=1.2,
           error_message=""
       )
   ```

6. **Export CSV** (FR-045 to FR-047):
   ```csv
   filename,mode,peak_label,center,amplitude,FWHM,shape,chi2,R2
   sample_raman.txt,Raman,D-Band,1350.2,505.3,48.7,0.5,12.5,0.987
   sample_raman.txt,Raman,G-Band,1581.1,795.6,38.2,0.5,12.5,0.987
   ```

7. **Save Project** (FR-051 to FR-055):
   ```python
   project_state = ProjectState(
       version="1.0.0",
       timestamp=datetime.utcnow().isoformat(),
       files=[spectrum_file],
       global_styling=StylingPreferences()
   )
   json_str = project_state.to_json()
   st.download_button("Download Project", json_str, file_name="project_state.json")
   ```

---

## Validation Summary

| Entity | Key Validations |
|--------|-----------------|
| SpectrumFile | Filename unique, mode valid, raw/processed data consistent |
| SpectrumData | X/Y same length, Y non-negative, X may be negative |
| ProcessingSettings | Parameter ranges (threshold 3-15, degree 1-10, etc.) |
| PeakDefinition | Center within X range, auto-bounds logical, positive amplitude/width |
| FitResult | Chi²/R² calculated, error messages actionable if failed |
| FittedPeak | Standard errors present, component curve matches total fit |
| ProjectState | Version string valid, timestamp ISO 8601, files list non-empty |
| StylingPreferences | Line widths 0.5-5.0, colors valid hex/Plotly names |

---

## Next Steps

- Generate `contracts/project-state-schema.json` (JSON Schema for ProjectState).
- Generate `quickstart.md` (developer guide for working with data model).
- Update agent context with data model classes.
