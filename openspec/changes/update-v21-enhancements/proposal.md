# Change: SpectralFit v2.1 Enhancements

## Why

User feedback from v2.0 deployment identified four critical usability and reliability issues:

1. **Manual mode switching friction** - Users with organized datasets (RM_*, PL_* naming) waste time manually toggling mode for each file
2. **Baseline failures on negative Y** - Workflow blocker when spectra contain negative intensity values (e.g., background-subtracted data, detector offset)
3. **Inflexible plot sizing** - Fixed-width plots hinder detailed inspection on varied display sizes
4. **Full-spectrum noise interference** - Users need to analyze specific spectral regions without contamination from noisy edges or irrelevant features

These issues reduce efficiency, block workflows, and limit analytical precision for research users.

## What Changes

### FR-12: Auto Mode Detection from Filename
- Detect `RM*` or `PL*` filename prefixes (case-insensitive) and auto-set mode on file load
- Display dismissible banner when auto-detection triggers
- Manual mode toggle always overrides auto-detection
- Save auto-detected flag in per-file state and project JSON

### FR-13: Baseline Error Handling for Negative Y Values (**BREAKING**)
- **BREAKING:** Modify `SpectrumData` validation to allow negative Y values
- Apply automatic vertical shift internally within baseline algorithms when negative Y detected
- Log shift amount in project state for transparency
- Add tooltip explaining transparent handling

### FR-14: Adjustable Plot Width
- Add plot width control with 4 presets: Compact (60%), Standard (75%), Wide (90%), Full (100%)
- Apply globally across all tabs and persist in session state
- Maintain Plotly interactivity at all widths

### FR-15: X-Range Selection for Focused Processing
- Add "Processing Range" controls (checkbox + X min/max inputs) in Pre-process tab
- When enabled, limit spike removal, baseline correction, and fitting to specified X range
- Visual indicators: dashed boundary lines, 30% opacity for out-of-range data
- Save per-file X range settings and export metadata in Master CSV

### Export Schema Update
New CSV columns: `auto_detected`, `x_range_limited`, `x_min`, `x_max`

## Impact

**Affected specs:**
- `mode-selection` (new) - ADDED auto-detection capability
- `baseline-correction` (new) - ADDED negative Y handling, MODIFIED validation
- `visualization-settings` (new) - ADDED plot width control
- `processing-range` (new) - ADDED X-range filtering for all pipeline stages

**Affected code:**
- `src/models/spectrum.py` - Relax Y validation to allow negative values
- `src/ui/sidebar.py` - Add mode auto-detection logic and plot width control
- `src/processing/baseline.py` - Add automatic Y-shift wrapper
- `src/ui/preprocess_tab.py` - Add X-range controls and range-aware processing
- `src/ui/fit_tab.py` - Add "Fit only within X range" checkbox
- `src/visualization/plotter.py` - Add width parameter, X-range visual indicators
- `src/io/export.py` - Add new CSV columns
- `src/io/project_io.py` - Update JSON schema for new fields

**Breaking changes:**
- **FR-13:** `SpectrumData` now accepts negative Y values; existing validation tests must be updated

**Backward compatibility:**
- v2.0 project JSON files load successfully with defaults for missing fields
- Existing CSV analysis tools unaffected (new columns appended at end)
