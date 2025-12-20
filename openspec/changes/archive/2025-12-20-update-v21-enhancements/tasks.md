# Implementation Tasks: v2.1 Enhancements

## 1. Core Data Model Updates (FR-13)

- [x] 1.1 Update `SpectrumData.__post_init__` validation to allow negative Y values
- [x] 1.2 Update docstring to document negative Y support
- [ ] 1.3 Update unit tests for `SpectrumData` to cover negative Y cases
- [ ] 1.4 Add test fixtures with negative Y spectra

## 2. Baseline Negative Y Handling (FR-13)

- [x] 2.1 Create `apply_auto_shift()` utility in `src/processing/baseline.py`
- [x] 2.2 Wrap polynomial baseline with auto-shift logic
- [x] 2.3 Wrap ALS baseline with auto-shift logic
- [x] 2.4 Add shift amount to processing state (per-file)
- [x] 2.5 Add tooltip in baseline controls explaining transparent handling
- [ ] 2.6 Unit tests for auto-shift with negative Y data
- [x] 2.7 Extend `plot_preview()` with baseline_preview and y_corrected_preview parameters
- [x] 2.8 Add preview baseline trace rendering (red dashed line) in `plotter.py`
- [x] 2.9 Add preview corrected spectrum rendering (green semi-transparent) in `plotter.py`
- [x] 2.10 Add preview computation logic with caching in `preprocess_tab.py`
- [x] 2.11 Implement cache key generation (filename + algorithm + params)
- [x] 2.12 Add session state cache validation and recomputation logic
- [x] 2.13 Modify "Run Baseline Correction" button to use cached preview
- [x] 2.14 Add preview cache clearing on "Reset to Raw" button
- [x] 2.15 Update preview plot section to pass preview data to plotter
- [x] 2.16 Add conditional caption updates based on preview state
- [ ] 2.17 Unit tests for preview caching and invalidation logic

## 3. Auto Mode Detection (FR-12)

- [x] 3.1 Add `detect_mode_from_filename()` function in `src/processing/parser.py`
- [x] 3.2 Integrate detection in file upload logic (`src/ui/sidebar.py`)
- [x] 3.3 Add `auto_detected` field to `SpectrumFile` model
- [x] 3.4 Implement dismissible banner in sidebar (Streamlit toast or expander)
- [x] 3.5 Ensure manual toggle overrides auto-detection
- [ ] 3.6 Unit tests for filename pattern matching (RM*, PL*, edge cases)

## 4. Plot Width Control (FR-14)

- [x] 4.1 Add plot width state to session state (`plot_width_preset`)
- [x] 4.2 Create width control widget in sidebar (radio/selectbox for 4 presets)
- [x] 4.3 Update `plotter.py` to accept width parameter and apply to all plots
- [x] 4.4 Apply width globally across Pre-process, Fit Model, Visualize tabs
- [x] 4.5 Save plot width in project JSON schema
- [x] 4.6 Verify Plotly interactivity preserved at all widths

## 5. X-Range Selection UI (FR-15)

- [x] 5.1 Add "Processing Range" section in `src/ui/preprocess_tab.py`
- [x] 5.2 Add checkbox: "Limit to X range" with default unchecked
- [x] 5.3 Add numeric inputs for X min/max (auto-populated from data range)
- [x] 5.4 Add per-file X range state (`x_range_enabled`, `x_min`, `x_max`)
- [x] 5.5 Display units (cm⁻¹ or nm) based on mode

## 6. X-Range Processing Logic (FR-15)

- [ ] 6.1 Update spike removal to detect full spectrum, replace only within range
- [ ] 6.2 Update baseline algorithms to compute only on X-range data
- [x] 6.3 Add "Fit only within X range" checkbox in Fit tab
- [x] 6.4 Update fitting logic to filter data by X range when enabled
- [ ] 6.5 Unit tests for range-limited processing (spike, baseline, fit)

## 7. X-Range Visualization (FR-15)

- [x] 7.1 Add vertical dashed lines at X min/max boundaries in `plotter.py`
- [x] 7.2 Render out-of-range data at 30% opacity
- [x] 7.3 Add shaded region or color distinction for active range
- [x] 7.4 Ensure visual indicators work across all plot types (raw, baseline, fit)

## 8. Export Schema Updates

- [x] 8.1 Add `auto_detected` column to Master CSV export
- [x] 8.2 Add `x_range_limited`, `x_min`, `x_max` columns to Master CSV
- [x] 8.3 Update `src/io/export.py` to populate new fields from state
- [x] 8.4 Verify CSV column order (new columns appended at end)

## 9. Project I/O Updates

- [x] 9.1 Update project JSON schema to include new fields per file
- [x] 9.2 Add default values for missing fields when loading v2.0 projects
- [x] 9.3 Update `src/io/project_io.py` save/load functions
- [ ] 9.4 Test backward compatibility with v2.0 project files
- [ ] 9.5 Update JSON schema example in documentation

## 10. Integration and Testing

- [ ] 10.1 Integration test: Auto-detect mode from RM_sample.txt and PL_test.txt
- [ ] 10.2 Integration test: Baseline correction with negative Y spectrum
- [ ] 10.3 Integration test: Plot width changes apply across all tabs
- [ ] 10.4 Integration test: X-range limiting affects spike/baseline/fit correctly
- [ ] 10.5 Integration test: Export CSV contains all new columns with correct values
- [ ] 10.6 Manual QA: Load v2.0 project, verify defaults applied, no errors
- [ ] 10.7 Manual QA: Visual indicators (boundaries, opacity) render correctly

## 11. Documentation

- [ ] 11.1 Update README with v2.1 feature summary
- [ ] 11.2 Add tooltips/help text for all new controls
- [ ] 11.3 Update example workflow in documentation
- [ ] 11.4 Document breaking change (negative Y support) in changelog
