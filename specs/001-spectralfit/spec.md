# Feature Specification: SpectralFit - Raman & Photoluminescence Spectrum Analysis Tool

**Feature Branch**: `001-spectralfit`
**Created**: 2025-12-13
**Status**: Draft
**Input**: User description: "Raman and Photoluminescence Spectrum Analysis Tool"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean and Baseline Correct Single Spectrum (Priority: P1)

A researcher loads a single Raman or PL spectrum, removes cosmic-ray spikes, corrects the fluorescence baseline, and exports the cleaned data for further analysis or publication.

**Why this priority**: Core data cleaning workflow that must work reliably before any peak fitting. Delivers immediate value by producing publication-ready baseline-corrected spectra.

**Independent Test**: Can be fully tested by uploading a spectrum file, adjusting spike removal sensitivity, selecting and applying a baseline correction method, and verifying the corrected spectrum is displayed and exportable.

**Acceptance Scenarios**:

1. **Given** a researcher has a Raman spectrum with 2-3 cosmic-ray spikes and fluorescence background, **When** they upload the .txt file, adjust spike sensitivity to 6.0, click "Auto Remove Spikes", select polynomial baseline (degree 3), and view the corrected spectrum, **Then** spikes are removed, baseline is subtracted, and the cleaned spectrum is displayed with residuals.

2. **Given** a PL spectrum with complex fluorescence background, **When** they select ALS baseline correction with default parameters (�=10000, p=0.001) and enable "Show Baseline", **Then** the ALS baseline overlay appears on the plot hugging the lower envelope, and baseline-corrected data is ready for fitting.

3. **Given** incorrect spike removal settings were applied, **When** the user clicks "Reset to Raw", **Then** the original unmodified spectrum is restored and all pre-processing can be restarted.

---

### User Story 2 - Fit and Decompose Overlapping Peaks (Priority: P2)

A researcher fits multiple overlapping Voigt peaks to a baseline-corrected spectrum, adjusts initial guesses, obtains fitted peak parameters (center, width, amplitude), and evaluates fit quality.

**Why this priority**: Peak fitting is the primary analytical goal. Without this, users cannot extract quantitative peak parameters needed for research.

**Independent Test**: Can be tested independently by loading a pre-cleaned spectrum (or using Story 1 output), adding 2-5 peak guesses to the peak table, running the fit, and verifying that fitted parameters and quality metrics (ǲ, R�) are displayed.

**Acceptance Scenarios**:

1. **Given** a baseline-corrected Raman spectrum with 3 visible peaks (D-band ~1350 cm{�, G-band ~1580 cm{�, 2D-band ~2700 cm{�), **When** the user clicks "Auto-Find Peaks" and then clicks "Run Fit", **Then** the system detects 3 peaks, populates the peak table with initial guesses, fits Voigt profiles, displays fitted curves overlaid on data, and shows ǲ and R� metrics.

2. **Given** the user manually enters peak centers in the peak table (e.g., 1350, 1580, 2700 cm{� for Raman mode), **When** they click "Run Fit", **Then** the fitter constrains centers to �5 cm{� of the guess, fits amplitudes and widths within auto-calculated bounds, and displays individual peak components in different colors.

3. **Given** the fit fails to converge due to poor initial guesses, **When** the fitting completes, **Then** a clear error message appears stating "Fit did not converge. Suggestions: (1) Check center guesses, (2) Widen bounds, (3) Reduce peak count."

4. **Given** the user wants to override auto-bounds, **When** they enable "Advanced" mode checkbox, **Then** additional columns (Center Min, Center Max, Width Min, Width Max, Amplitude Max) appear in the peak table for manual editing.

---

### User Story 3 - Style and Export Publication-Quality Figures (Priority: P3)

A researcher customizes plot appearance (colors, line styles, widths), toggles individual peak components on/off, and exports the figure as PNG or interactive HTML for publication or presentation.

**Why this priority**: Publication-ready visualization is essential for communicating results, but can be done after fitting works. Styling is often iterative and less critical than obtaining correct fit results.

**Independent Test**: Can be tested by loading a fitted spectrum (from Story 2 output), opening the styling panel, changing peak colors and line widths, toggling component visibility in the legend, and exporting PNG and HTML files.

**Acceptance Scenarios**:

1. **Given** a fitted spectrum with 3 peaks displayed, **When** the user opens the styling panel and changes peak colors to red, green, and blue, **Then** the individual Voigt component curves update to the selected colors in the plot.

2. **Given** the composite plot shows data, fit, and components, **When** the user clicks a peak label in the legend to hide it, **Then** that peak's component curve disappears from the plot, and the total fit curve updates accordingly (if interactive legend allows).

3. **Given** a styled plot ready for publication, **When** the user clicks "Download PNG", **Then** a high-resolution static image file (spectralfit_plot_{filename}_{timestamp}.png) downloads with all current styling applied.

4. **Given** the user wants an interactive figure, **When** they click "Download HTML", **Then** a self-contained HTML file downloads with full interactivity (zoom, pan, hover tooltips).

---

### User Story 4 - Batch Load and Process Multiple Spectra (Priority: P4)

A researcher uploads 5-50 spectra from an experimental run, switches between files, applies cleaning and fitting to each individually, and exports a master CSV with all fitted peak parameters.

**Why this priority**: Batch loading improves workflow efficiency, but each file is still processed individually (no batch processing automation). This is a convenience feature for handling multiple datasets in one session.

**Independent Test**: Can be tested by uploading 3-5 .txt files, using the file selector dropdown to switch between them, verifying each file retains its own settings (spike threshold, baseline params, peak table), and exporting a combined CSV with all files' results.

**Acceptance Scenarios**:

1. **Given** a researcher has 10 Raman spectra from different samples, **When** they upload all 10 files via the file uploader, **Then** a dropdown appears listing all 10 filenames, and the first file is displayed.

2. **Given** 3 files are loaded and the user has processed file #1 (removed spikes, corrected baseline, fitted peaks), **When** they switch to file #2 via the dropdown, **Then** file #2's raw data is displayed, and file #1's state (settings, fit results) is preserved in memory.

3. **Given** all files have been fitted, **When** the user clicks "Download CSV", **Then** a single master CSV file downloads containing rows for all peaks from all files, with columns: filename, mode, peak_label, center, amplitude, FWHM, shape, chi2, R2.

4. **Given** file parsing encounters a malformed file (e.g., 3 columns or text headers), **When** the file is uploaded, **Then** a warning message appears ("File {name} could not be parsed: expected 2 numeric columns, found {details}") and the file is skipped.

---

### User Story 5 - Save and Reload Project State (Priority: P5)

A researcher saves the entire session (all files, settings, peak tables, styling) to a JSON file, closes the app, and later reloads the project to continue analysis from the exact same state.

**Why this priority**: Project persistence enables reproducibility and iterative refinement, but is not critical for initial analysis workflows. Can be added after core analysis features work.

**Independent Test**: Can be tested by loading files, applying settings and fits, clicking "Save Project" to download JSON, restarting the app, clicking "Load Project", uploading the JSON, and verifying all settings and results are restored.

**Acceptance Scenarios**:

1. **Given** a researcher has processed 5 files with various baseline settings and fit results, **When** they click "Save Project", **Then** a JSON file (project_state.json) downloads containing version, timestamp, per-file settings (mode, de-spike threshold, baseline algorithm and params), peak tables, and styling preferences.

2. **Given** a saved project JSON file, **When** the user clicks "Load Project" and selects the JSON, **Then** the app attempts to restore all settings; if referenced .txt files are not yet uploaded, a warning lists missing files and allows the user to re-upload them.

3. **Given** a project is loaded successfully, **When** the user navigates to a file that was previously fitted, **Then** the fitted curves, peak table, and styling are restored exactly as saved.

---

### Edge Cases

- **Negative Raman shifts**: Raman spectra may contain negative wavenumber values (e.g., -680 to +500 cm{�). System must preserve and display negative values correctly in plots and exports.

- **Very noisy spectra**: Modified Z-score spike detection with threshold <5.0 may remove legitimate signal peaks. User must be able to adjust threshold and preview results before applying.

- **Pathological baselines**: Some spectra have multi-feature backgrounds that cannot be fit by low-degree polynomial or require ALS tuning. System must allow user to try different algorithms and parameters, and must not crash or hang if baseline fitting fails.

- **Single-peak spectra**: Auto-find peaks should detect at least 1 peak; fitting should work with N=1 peak without errors.

- **Fit non-convergence**: If L-M solver fails to converge, system must display actionable error message (not cryptic stack trace) and allow user to modify guesses and retry without reloading file.

- **Empty or all-zero intensity**: If a file contains all zeros or constant intensity, baseline correction and fitting are undefined. System should detect and warn user ("Spectrum appears flat or empty; cannot process").

- **Very wide or very narrow peaks**: Width bounds must adapt to spectral resolution; peaks narrower than 2-3 data points cannot be reliably fitted, peaks wider than 50% of range are likely baseline artifacts.

- **Overlapping peak centers**: If two peaks are initialized with centers within 1-2 FWHM, fitting may fail or merge peaks. System should warn if detected ("Peaks {i} and {j} are very close; consider reducing peak count or adjusting guesses").

## Requirements *(mandatory)*

### Functional Requirements

#### Data Ingestion

- **FR-001**: System MUST accept plain text (.txt) files with exactly two numeric columns (X, Y) separated by tabs or commas, with no headers.
- **FR-002**: System MUST auto-detect delimiter (tab or comma) or allow user to select delimiter if auto-detection fails.
- **FR-003**: System MUST parse numeric data including scientific notation (e.g., 6.02E+02) and preserve negative X values.
- **FR-004**: System MUST skip non-numeric rows and warn user if any rows are skipped during parsing.
- **FR-005**: System MUST support batch upload of 1-100 .txt files in a single session.
- **FR-006**: System MUST provide a file selector dropdown listing all successfully loaded files by filename.
- **FR-007**: Each file MUST maintain independent state (raw data, de-spiked data, baseline settings, peak table, fit results) throughout the session.

#### Mode Selection

- **FR-008**: System MUST provide a mode toggle with two options: "Raman (cm{�)" and "PL (nm)".
- **FR-009**: Mode selection MUST affect axis labels, fitting parameter bounds, and default ALS settings (if implemented).
- **FR-010**: Switching modes MUST update all plots and fitting constraints immediately.

#### Cosmic-Ray Removal

- **FR-011**: System MUST implement modified Z-score spike detection using Median Absolute Deviation (MAD).
- **FR-012**: System MUST provide a spike sensitivity slider (range 3.0-15.0, default 6.0).
- **FR-013**: System MUST preview detected spikes visually on the plot (e.g., red overlay markers) before removal.
- **FR-014**: System MUST provide "Auto Remove Spikes" button that replaces spike values with local median of �2 neighbors.
- **FR-015**: System MUST provide "Reset to Raw" button that reverts current file to original unmodified data.
- **FR-016**: Spike removal MUST be reversible only via "Reset to Raw" (no undo within a processing session).

#### Baseline Correction

- **FR-017**: System MUST support polynomial baseline subtraction with degree 1-10 (user-selectable).
- **FR-018**: System MUST support Asymmetric Least Squares (ALS) baseline subtraction with adjustable � (smoothness, range 1e3-1e6, default 1e4) and p (asymmetry, range 0.001-0.1, default 0.001).
- **FR-019**: System MUST provide a dropdown to select baseline algorithm ("Polynomial" or "ALS").
- **FR-020**: System MUST calculate baseline from de-spiked data (or raw data if de-spiking not applied).
- **FR-021**: System MUST subtract baseline to produce baseline-corrected intensity in original raw units (no normalization).
- **FR-022**: System MUST provide "Show Baseline" checkbox to overlay calculated baseline on the main plot.
- **FR-023**: System MUST provide "Show Residuals" checkbox to display baseline fit residuals in a separate subplot or panel.
- **FR-024**: Changing baseline algorithm or parameters MUST update the plot immediately and reset any previous fit results.

#### Peak Fitting

- **FR-025**: System MUST provide an editable peak table with columns: Label (text), Center (numeric), Amplitude (numeric), Width (FWHM, numeric), Shape (0-1, Voigt mixing), Color (hex string).
- **FR-026**: Users MUST be able to add, remove, and edit rows in the peak table.
- **FR-027**: System MUST provide "Auto-Find Peaks" button that populates the peak table with detected peaks using automated peak detection algorithms.
- **FR-028**: Auto-find peaks MUST estimate Center (X at maximum), Amplitude (Y at maximum), and FWHM (width at half-maximum) for each detected peak.
- **FR-029**: System MUST auto-calculate fitting bounds based on mode:
  - Raman: center � 5 cm{�, width min = 2-3 spectral steps, width max = 50% of range, amplitude max = 1.5-2.0� max(Y)
  - PL: center � 30 nm, width min = 2-3 spectral steps, width max = 50% of range, amplitude max = 1.5-2.0� max(Y)
- **FR-030**: System MUST provide "Advanced" checkbox that reveals additional columns (Center Min, Center Max, Width Min, Width Max, Amplitude Max) for manual bound editing.
- **FR-031**: System MUST fit peaks using Voigt profiles (convolution of Gaussian and Lorentzian).
- **FR-032**: System MUST use Levenberg-Marquardt nonlinear least squares fitting algorithm.
- **FR-033**: System MUST provide "Run Fit" button that executes fitting with current peak table and bounds.
- **FR-034**: System MUST display fit status: "Ready to fit" (before fitting), "Fitting in progress..." (during), "Fit converged in X s. ǲ = Y, R� = Z" (success), or "Fit did not converge. Suggestions: ..." (failure).
- **FR-035**: On convergence failure, system MUST provide actionable error message with specific suggestions (e.g., check guesses, widen bounds, reduce peak count).
- **FR-036**: System MUST calculate and display fit quality metrics: ǲ (sum of squared residuals) and R� (coefficient of determination).
- **FR-037**: Fitted parameters (center, amplitude, width, shape) MUST be cached for export and plotting.

#### Visualization

- **FR-038**: System MUST display a composite plot with two subplots: top (3/4 height) showing data + total fit + individual components, bottom (1/4 height) showing residuals (Data - Fit) vs X.
- **FR-039**: System MUST provide interactive plotting capabilities with zoom, pan, and hover tooltips.
- **FR-040**: System MUST provide legend checkboxes to toggle visibility of individual peak components and total fit curve.
- **FR-041**: System MUST label X-axis as "Raman Shift (cm{�)" for Raman mode or "Wavelength (nm)" for PL mode.
- **FR-042**: System MUST label Y-axis as "Intensity (a.u.)" or allow user-customizable label.
- **FR-043**: System MUST provide styling panel (collapsible or in separate tab) with controls for per-peak color, line style (solid/dashed/dotted), line width (0.5-5 pt), and data marker style (dots/crosses/none).
- **FR-044**: Plot rendering and re-rendering MUST complete in <500 ms when toggling components or adjusting styling.

#### Export

- **FR-045**: System MUST provide "Download CSV" button that exports a master CSV file containing all fitted peaks from all files in the current session.
- **FR-046**: Master CSV MUST include columns: filename, mode, peak_label, center, amplitude, FWHM, shape, chi2 (or R2).
- **FR-047**: Master CSV MUST contain values in raw units (not normalized) with comma delimiters.
- **FR-048**: System MUST provide "Download PNG" button that exports the current composite plot as a static image.
- **FR-049**: System MUST provide "Download HTML" button that exports the current plot as a self-contained interactive HTML file with full interactivity preserved (optional but recommended).
- **FR-050**: Export file naming MUST follow patterns: spectralfit_export_{timestamp}.csv, spectralfit_plot_{filename}_{timestamp}.png/html.

#### Project State

- **FR-051**: System MUST provide "Save Project" button that downloads a JSON file containing session state.
- **FR-052**: Project JSON MUST include: version, timestamp, per-file settings (mode, de-spike threshold, baseline algorithm and params, peak table), and styling preferences.
- **FR-053**: System MUST provide "Load Project" button that accepts a JSON file and restores session state.
- **FR-054**: On project load, if referenced .txt files are missing, system MUST warn user and list missing files, allowing user to re-upload them.
- **FR-055**: Project JSON schema MUST be versioned to support future compatibility.

### Key Entities

- **Spectrum File**: Represents a single uploaded .txt file with X (wavenumber or wavelength) and Y (intensity) columns. Attributes: filename, raw X/Y data, de-spiked Y data, baseline-corrected Y data, associated mode (Raman/PL), processing settings (spike threshold, baseline algorithm/params).

- **Peak Definition**: Represents a single peak to be fitted. Attributes: label (text), initial guesses (center, amplitude, width, shape), fitting bounds (center min/max, width min/max, amplitude max), fitted parameters (center, amplitude, width, shape), fit quality contribution.

- **Fit Result**: Represents the outcome of fitting a spectrum. Attributes: fitted parameters for all peaks, total fit curve, residuals, quality metrics (ǲ, R�), convergence status, error messages (if any).

- **Project State**: Represents the entire session. Attributes: version, timestamp, list of spectrum files with their settings and results, global styling preferences (colors, line styles, widths).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can load a spectrum, remove spikes, correct baseline, and export cleaned data in under 3 minutes with default settings.

- **SC-002**: Spike detection and baseline correction complete in 1-3 seconds on typical lab laptops for spectra with 1,000-10,000 data points.

- **SC-003**: Fitting 2-5 peaks with Voigt profiles converges in under 2 seconds for typical Raman/PL spectra with good initial guesses.

- **SC-004**: 90% of typical Raman/PL spectra achieve R� > 0.95 when fitted with appropriate peak count and default settings.

- **SC-005**: Users can load 10-20 spectra, fit all of them, and export a master CSV in under 15 minutes.

- **SC-006**: Auto-find peaks correctly detects 80% or more of prominent peaks (SNR > 5:1) in typical spectra without manual tuning.

- **SC-007**: Plot rendering and interaction (zoom, pan, toggle components) remains smooth (<500 ms response time) for spectra up to 20,000 points.

- **SC-008**: Exported PNG figures are publication-quality (300+ DPI, clear labels, customizable colors/styles).

- **SC-009**: Saved project state can be reloaded in a new session and reproduces identical fit results (same parameters, same metrics).

- **SC-010**: Error messages for common issues (file format errors, fit non-convergence, missing files) are actionable and reduce user support requests by 70% compared to generic error messages.

## Assumptions

- Users have basic familiarity with spectroscopy concepts (peak positions, widths, baseline correction).
- Input files are generated by standard spectroscopy instruments and follow the two-column numeric format.
- Users have access to a modern web browser (Chrome, Firefox, Edge, Safari) and lab computers with at least 8 GB RAM.
- Typical spectra contain 1,000-10,000 data points; larger spectra (>20,000 points) may experience slower performance.
- Users process spectra one at a time (no batch processing automation); batch loading is for convenience only.
- Peak labels are optional and user-defined; no pre-defined peak library or auto-labeling (e.g., "D-band", "G-band") is provided.
- Data retention is session-based (no server-side storage); users must save project JSON files locally for reproducibility.
- Performance targets assume modern lab laptops (Intel i5/i7 or equivalent, 8+ GB RAM, SSD).
- Voigt profiles are sufficient for all peak shapes; asymmetric or alternative line shapes are not required in version 1.0.
