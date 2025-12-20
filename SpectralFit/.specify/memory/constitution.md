# SpectralFit Constitution

<!--
Sync Impact Report:
- Version change: [initial template] → 1.0.0 (initial ratification)
- Modified principles: None (new constitution)
- Added sections:
  * Core Principles (5 principles)
  * Development Standards
  * User Experience Requirements
  * Governance
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md (Constitution Check section compatible)
  ✅ spec-template.md (User scenarios and requirements align)
  ✅ tasks-template.md (Phase structure supports principles)
- Follow-up TODOs: None
-->

## Core Principles

### I. Physics-Aware Design

SpectralFit MUST maintain distinct operating modes (Raman and Photoluminescence) with mode-specific handling. Each mode SHALL enforce appropriate units (cm⁻¹ for Raman, nm for PL), default parameter bounds, and axis labels. The application MUST preserve physical units throughout the pipeline—negative wavenumbers for Raman MUST be supported, and all intensity values MUST remain in raw detector units (no automatic normalization).

**Rationale**: Spectroscopy data has domain-specific constraints. Raman spectra can have negative shifts; mixing modes or auto-normalizing destroys scientific validity. Physics-aware defaults reduce user error and ensure reproducible analysis.

### II. Linear Processing Pipeline

The workflow MUST follow a strict linear sequence: data ingestion → cosmic-ray removal → baseline correction → multi-peak fitting → visualization and export. Each stage MUST operate on the output of the previous stage. Users MUST be able to reset to raw data and restart the pipeline at any point.

**Rationale**: Spectroscopy analysis has a natural order. Fitting before baseline correction produces nonsense results. A linear workflow enforces correctness, prevents state confusion, and matches researcher mental models.

### III. Robust Pre-Processing (NON-NEGOTIABLE)

Spike detection MUST use the modified Z-score algorithm (MAD-based, threshold 3.0–15.0, default 6.0). Baseline correction MUST support both polynomial (degree 1–10) and Asymmetric Least Squares (ALS) algorithms. All pre-processing operations MUST be previewed visually before application and MUST be reversible via "Reset to Raw."

**Rationale**: Cosmic-ray spikes and fluorescence backgrounds corrupt spectral analysis. Manual baseline fitting is tedious and irreproducible. Robust, algorithm-based preprocessing with visual preview ensures quality and reproducibility.

### IV. Constrained Nonlinear Fitting

Peak fitting MUST use Voigt profiles (lmfit backend with Levenberg–Marquardt). Center bounds MUST be auto-calculated based on mode (Raman: ±5 cm⁻¹, PL: ±30 nm). Width bounds MUST prevent zero-width or unreasonably broad peaks (minimum 2–3 spectral resolution steps, maximum 50% of range). Amplitude MUST be constrained to [0, 1.5–2.0× max intensity]. Fitting MUST provide actionable error messages on convergence failure (e.g., "Check center guesses, widen bounds, reduce peak count").

**Rationale**: Unconstrained fitting produces unphysical results (negative amplitudes, peaks drifting to noise). Mode-aware auto-bounds encode domain knowledge, prevent common errors, and improve convergence. Voigt profiles are the standard spectroscopy line shape.

### V. Simplicity and Clarity

The UI MUST default to simple controls with sensible defaults ("just works" for typical spectra). Advanced features (custom bounds, ALS tuning) MUST be hidden behind opt-in checkboxes. Error messages MUST be clear and actionable. The application MUST NOT implement batch processing (apply settings to all files at once), global optimization algorithms, alternative line shapes, or parametric fit exports in the initial version.

**Rationale**: Researchers want robust, reproducible results quickly. Complexity overwhelms users. Simple defaults with progressive disclosure (advanced mode) balance power and usability. Explicit non-goals (batch processing, etc.) prevent scope creep.

## Development Standards

### File Format and Data Handling

Input files MUST be plain text (`.txt`), tab-delimited or comma-delimited, exactly two numeric columns with NO headers. The parser MUST handle scientific notation, skip non-numeric rows, and warn users of malformed data. Each uploaded file MUST maintain independent state (de-spike settings, baseline parameters, peak table, fit results) for the session duration.

**Rationale**: Instrument output is typically headerless two-column text. Robust parsing handles real-world data quirks. Per-file state isolation prevents cross-contamination and supports batch loading without batch processing.

### Algorithm Implementation

De-spiking: Modified Z-score with MAD (Iglewicz & Hoaglin, 1993). Baseline: Polynomial (scipy) or ALS (Eilers & Boelens, 2005). Fitting: lmfit VoigtModel with Levenberg–Marquardt. All algorithms MUST complete in 1–3 seconds on typical lab laptops (10³–10⁴ data points). Plotting MUST re-render in <500 ms.

**Rationale**: Standard chemometrics and spectroscopy algorithms ensure correctness and reproducibility. Performance targets match user expectations for interactive analysis.

### Testing and Validation

All fit results MUST display χ² (or reduced χ²) and R² metrics. The application MUST handle edge cases gracefully (single-peak spectra, very noisy data, pathological baselines) and show clear error messages with recovery options (retry with different settings without reloading file).

**Rationale**: Users need quality metrics to assess fits. Graceful error handling prevents frustration and data loss.

## User Experience Requirements

### Default Settings

Mode-specific defaults MUST work for typical spectra without tuning: spike sensitivity 6.0, polynomial degree 2–3, ALS λ~10⁴ and p~0.001, auto-find peaks detecting 2–5 prominent features. The application MUST provide tooltips and help text for all controls explaining parameters, ranges, and physical meaning.

**Rationale**: Good defaults reduce onboarding friction. Tooltips educate users and prevent misuse.

### Export and Project State

Master CSV export MUST contain all fitted peaks from all files (columns: filename, mode, peak_label, center, amplitude, FWHM, shape, chi2/R2) in raw units with comma delimiters and NO extra metadata. Figure export MUST support PNG (static) and HTML (interactive Plotly). Project save/load MUST preserve mode, de-spike threshold, baseline settings, peak table, and styling via JSON.

**Rationale**: Simple, raw-value CSV is universally compatible with downstream analysis. PNG for publication, HTML for exploration. Project state enables reproducibility and iterative refinement.

### Visualization

The main plot MUST show data + total fit + individual Voigt components + residuals in a composite layout (top subplot 3/4 height for fits, bottom 1/4 for residuals). Users MUST be able to toggle component visibility via legend checkboxes, customize colors/line styles/widths, and zoom/pan interactively (Plotly). Axis labels MUST reflect mode (Raman: "Raman Shift (cm⁻¹)", PL: "Wavelength (nm)").

**Rationale**: Publication-quality plots require full control over styling. Interactive plots aid exploration. Residuals reveal fit quality. Mode-aware labels prevent unit confusion.

## Governance

This constitution supersedes all other development practices and design decisions. Any feature addition, algorithm change, or UX modification MUST comply with the Core Principles. Non-goals (batch processing, alternative line shapes, etc.) MUST NOT be implemented in version 1.0 unless this constitution is amended.

### Amendment Procedure

Amendments require (1) written justification referencing user needs or technical constraints, (2) approval from the project maintainer, and (3) a migration plan if existing features are affected. Version bumps follow semantic versioning:
- **MAJOR**: Backward-incompatible principle changes (e.g., removing a mode, changing file format).
- **MINOR**: New principles, new sections, or expanded guidance (e.g., adding a new baseline algorithm).
- **PATCH**: Clarifications, wording fixes, non-semantic refinements.

### Compliance Review

All pull requests and code reviews MUST verify compliance with Core Principles. Complexity (e.g., adding a third mode, implementing global optimization) MUST be justified in plan.md Complexity Tracking table with documented simpler alternatives rejected.

**Version**: 1.0.0 | **Ratified**: 2025-12-13 | **Last Amended**: 2025-12-13
