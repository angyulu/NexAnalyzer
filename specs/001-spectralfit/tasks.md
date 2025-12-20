# Tasks: SpectralFit - Raman & Photoluminescence Spectrum Analysis Tool

**Input**: Design documents from `/specs/001-spectralfit/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Tests are NOT included (not explicitly requested in specification).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `SpectralFit/src/`, `SpectralFit/tests/` at repository root
- Paths shown below assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure per plan.md (SpectralFit/, src/, tests/, fixtures/)
- [ ] T002 Initialize Python project with requirements.txt (Streamlit>=1.28.0, NumPy>=1.24.0, SciPy>=1.11.0, lmfit>=1.2.0, Plotly>=5.17.0, Pandas>=2.0.0)
- [ ] T003 [P] Create requirements-dev.txt (pytest>=7.4.0, pytest-cov>=4.1.0, black>=23.9.0, mypy>=1.5.0, ruff>=0.0.290)
- [ ] T004 [P] Create app.py Streamlit entry point with basic structure (imports, title, session state initialization)
- [ ] T005 [P] Create README.md with installation and usage instructions
- [ ] T006 [P] Create .gitignore for Python/Streamlit projects (venv/, __pycache__/, .streamlit/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Create Mode enum in SpectralFit/src/models/__init__.py (Raman, PL)
- [ ] T008 [P] Create SpectrumData class in SpectralFit/src/models/spectrum.py (immutable X/Y arrays with validation)
- [ ] T009 [P] Create ProcessingSettings class in SpectralFit/src/models/spectrum.py (despike_threshold, baseline_algorithm, etc.)
- [ ] T010 [P] Create SpectrumFile class in SpectralFit/src/models/spectrum.py (filename, mode, raw_data, processed_data, settings, peak_table, fit_result)
- [ ] T011 [P] Create PeakDefinition class in SpectralFit/src/models/peak.py (label, center, amplitude, width_fwhm, shape, color, bounds)
- [ ] T012 [P] Create FitResult and FittedPeak classes in SpectralFit/src/models/peak.py (success, fitted_peaks, residuals, chi_squared, r_squared)
- [ ] T013 [P] Create ProjectState class in SpectralFit/src/models/project.py (version, timestamp, files list, global_styling)
- [ ] T014 [P] Create StylingPreferences class in SpectralFit/src/models/project.py (data_color, line_width, marker_style, etc.)
- [ ] T015 Create file parser in SpectralFit/src/processing/parser.py (parse_spectrum function using pandas, auto-delimiter detection, handle scientific notation, skip non-numeric rows)
- [ ] T016 Initialize session_state in app.py (mode='Raman', current_file=None, files={}, global_styling=StylingPreferences())
- [ ] T017 [P] Create sidebar.py in SpectralFit/src/ui/sidebar.py (mode toggle radio button, file uploader, file selector dropdown, project I/O buttons)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Clean and Baseline Correct Single Spectrum (Priority: P1) 🎯 MVP

**Goal**: Researcher can load spectrum, remove cosmic-ray spikes, correct fluorescence baseline, export cleaned data

**Independent Test**: Upload .txt file, adjust spike sensitivity, select baseline method, verify corrected spectrum displayed and exportable

### Implementation for User Story 1

- [ ] T018 [P] [US1] Implement modified Z-score de-spiking in SpectralFit/src/processing/despiking.py (remove_spikes function using scipy.stats.median_abs_deviation, threshold 3-15, replace spikes with local median)
- [ ] T019 [P] [US1] Implement polynomial baseline correction in SpectralFit/src/processing/baseline.py (baseline_polynomial function using scipy.polynomial, degree 1-10)
- [ ] T020 [P] [US1] Implement ALS baseline correction in SpectralFit/src/processing/baseline.py (baseline_als function using scipy.sparse, lambda 1e3-1e6, p 0.001-0.1, 10 iterations)
- [ ] T021 [US1] Create preprocess_tab.py in SpectralFit/src/ui/preprocess_tab.py (tab container with two sections: De-spiking and Baseline)
- [ ] T022 [US1] Add de-spiking UI in preprocess_tab.py (spike sensitivity slider 3.0-15.0 default 6.0, "Auto Remove Spikes" button, "Reset to Raw" button, spike preview overlay on plot)
- [ ] T023 [US1] Add baseline correction UI in preprocess_tab.py (algorithm dropdown "Polynomial"/"ALS", degree slider 1-10 or lambda/p sliders, "Show Baseline" checkbox, "Show Residuals" checkbox)
- [ ] T024 [US1] Implement Reset to Raw functionality (button in preprocess_tab that reverts processed_data to raw_data and clears fit_result)
- [ ] T025 [US1] Create basic plotter in SpectralFit/src/visualization/plotter.py (plot_spectrum function using Plotly, show data points, mode-aware axis labels)
- [ ] T026 [US1] Add baseline overlay to plotter (show calculated baseline curve on main plot when "Show Baseline" checked)
- [ ] T027 [US1] Add residual subplot to plotter (1/4 height subplot showing baseline residuals when "Show Residuals" checked)
- [ ] T028 [US1] Wire up preprocess tab in app.py (add to st.tabs, connect to session_state, update plot on parameter changes)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (load → despike → baseline → view → reset)

---

## Phase 4: User Story 2 - Fit and Decompose Overlapping Peaks (Priority: P2)

**Goal**: Researcher fits multiple Voigt peaks, obtains fitted parameters, evaluates fit quality

**Independent Test**: Load pre-cleaned spectrum (or use US1 output), add 2-5 peak guesses, run fit, verify parameters and χ²/R² displayed

### Implementation for User Story 2

- [ ] T029 [P] [US2] Implement auto-bounds calculation in PeakDefinition.__init__ (mode-aware: Raman ±5 cm⁻¹, PL ±30 nm, width 2-3 steps to 50% range, amplitude 0 to 2×max(Y))
- [ ] T030 [P] [US2] Implement auto-find peaks in SpectralFit/src/processing/fitting.py (auto_find_peaks function using scipy.signal.find_peaks, estimate center/amplitude/FWHM for each peak)
- [ ] T031 [US2] Implement Voigt fitting in SpectralFit/src/processing/fitting.py (fit_voigt_peaks function using lmfit.models.VoigtModel, Levenberg-Marquardt method='leastsq', return FitResult with success, fitted_peaks, residuals, chi²,  R², convergence_time, error_message)
- [ ] T032 [US2] Add actionable error messages to fitting (if convergence fails, set error_message="Fit did not converge. Suggestions: (1) Check center guesses, (2) Widen bounds, (3) Reduce peak count.")
- [ ] T033 [US2] Create fit_tab.py in SpectralFit/src/ui/fit_tab.py (tab container with peak table and fitting controls)
- [ ] T034 [US2] Add editable peak table in fit_tab.py (st.data_editor with columns: Label, Center, Amplitude, Width_FWHM, Shape, Color, user can add/remove/edit rows)
- [ ] T035 [US2] Add "Auto-Find Peaks" button in fit_tab.py (calls auto_find_peaks, populates peak table with detected peaks)
- [ ] T036 [US2] Add "Advanced" mode checkbox in fit_tab.py (reveals additional columns: Center_Min, Center_Max, Width_Min, Width_Max, Amplitude_Max for manual bound editing)
- [ ] T037 [US2] Add "Run Fit" button in fit_tab.py (large primary button, calls fit_voigt_peaks with current peak table and baseline-corrected data)
- [ ] T038 [US2] Add fit status display in fit_tab.py (below Run Fit button, shows "Ready to fit" / "Fitting in progress..." / "Fit converged in X s. χ² = Y, R² = Z" / "Fit failed: <error_message>")
- [ ] T039 [US2] Update plotter to show fitted curves (plot_fit function that shows data + total fit + individual peak components in different colors, 3/4 top subplot for fits, 1/4 bottom subplot for residuals)
- [ ] T040 [US2] Add fit quality metrics display in fit_tab.py (show χ² and R² with brief interpretation text, e.g., "R²=0.98 indicates excellent fit")
- [ ] T041 [US2] Wire up fit tab in app.py (add to st.tabs, connect peak table to session_state, update plot on fit completion)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (US1 cleans data, US2 fits peaks to cleaned data)

---

## Phase 5: User Story 3 - Style and Export Publication-Quality Figures (Priority: P3)

**Goal**: Researcher customizes plot appearance, toggles components, exports PNG/HTML

**Independent Test**: Load fitted spectrum (from US2 output), change colors/line widths, toggle component visibility, export PNG and HTML files

### Implementation for User Story 3

- [ ] T042 [P] [US3] Create styling.py in SpectralFit/src/visualization/styling.py (apply_styling function that updates Plotly figure with custom colors/line styles/widths from StylingPreferences)
- [ ] T043 [P] [US3] Add legend interactivity to plotter (Plotly showlegend=True, clickable legend to toggle individual peak components and total fit curve)
- [ ] T044 [P] [US3] Implement PNG export in SpectralFit/src/io/export.py (export_png function using plotly.io.write_image, 300+ DPI, filename pattern spectralfit_plot_{filename}_{timestamp}.png)
- [ ] T045 [P] [US3] Implement HTML export in SpectralFit/src/io/export.py (export_html function using plotly.io.write_html, self-contained with full interactivity)
- [ ] T046 [US3] Create export_tab.py in SpectralFit/src/ui/export_tab.py (tab container with composite plot, styling panel, export buttons)
- [ ] T047 [US3] Add styling panel in export_tab.py (collapsible st.expander with per-peak color pickers, line style dropdown solid/dash/dot, line width slider 0.5-5 pt, data marker style radio buttons)
- [ ] T048 [US3] Add "Download PNG" button in export_tab.py (st.download_button that calls export_png and downloads file)
- [ ] T049 [US3] Add "Download HTML" button in export_tab.py (st.download_button that calls export_html and downloads interactive Plotly figure)
- [ ] T050 [US3] Wire up export tab in app.py (add to st.tabs, connect styling preferences to session_state, update plot when styling changes)

**Checkpoint**: All core analysis features (US1 + US2 + US3) should now be functional (clean → fit → style → export)

---

## Phase 6: User Story 4 - Batch Load and Process Multiple Spectra (Priority: P4)

**Goal**: Researcher uploads 5-50 spectra, switches between files, processes each individually, exports master CSV

**Independent Test**: Upload 3-5 .txt files, switch between files via dropdown, verify each retains independent state, export combined CSV

### Implementation for User Story 4

- [ ] T051 [P] [US4] Update sidebar.py file uploader to accept multiple files (st.file_uploader with accept_multiple_files=True, max 100 files)
- [ ] T052 [P] [US4] Add file selector dropdown in sidebar.py (st.selectbox listing all loaded filenames, updates st.session_state['current_file'] on selection)
- [ ] T053 [US4] Implement per-file state management in app.py (when file selected, load that file's SpectrumFile from session_state['files'], update all UI components to show that file's data/settings/results)
- [ ] T054 [US4] Add file parsing error handling in parser.py (if file has !=2 columns or non-numeric data, raise ValueError with message "File {name} could not be parsed: expected 2 numeric columns, found {details}")
- [ ] T055 [US4] Display file parsing warnings in sidebar (if rows skipped during parsing, show st.warning with count)
- [ ] T056 [US4] Implement master CSV export in SpectralFit/src/io/export.py (export_master_csv function that iterates all files in session_state['files'], extracts fitted peaks, creates DataFrame with columns: filename, mode, peak_label, center, amplitude, FWHM, shape, chi2, R2)
- [ ] T057 [US4] Add "Download CSV" button in export_tab.py (st.download_button that calls export_master_csv, filename spectralfit_export_{timestamp}.csv)
- [ ] T058 [US4] Add file count status in sidebar (display "Loaded N files" below file uploader)

**Checkpoint**: All user stories 1-4 should work together (batch load → process each → export combined results)

---

## Phase 7: User Story 5 - Save and Reload Project State (Priority: P5)

**Goal**: Researcher saves entire session to JSON, closes app, reloads project to restore exact state

**Independent Test**: Load files, apply settings/fits, save project JSON, restart app, load project, verify all settings/results restored

### Implementation for User Story 5

- [ ] T059 [P] [US5] Implement JSON serialization in ProjectState class (to_dict method that converts all np.ndarray → list, handles None values, follows contracts/project-state-schema.json)
- [ ] T060 [P] [US5] Implement JSON deserialization in ProjectState class (from_dict classmethod that recreates ProjectState from JSON dict, converts lists → np.ndarray)
- [ ] T061 [P] [US5] Add optional "Include spectral data" checkbox in sidebar (if unchecked, exclude raw_data and processed_data arrays from JSON to reduce file size)
- [ ] T062 [US5] Implement project save in SpectralFit/src/io/project_io.py (save_project function that creates ProjectState from session_state, serializes to JSON string with version="1.0.0" and timestamp)
- [ ] T063 [US5] Implement project load in SpectralFit/src/io/project_io.py (load_project function that deserializes JSON, validates version, restores session_state, warns if .txt files missing)
- [ ] T064 [US5] Add "Save Project" button in sidebar (st.download_button that calls save_project, filename project_state_{timestamp}.json)
- [ ] T065 [US5] Add "Load Project" button in sidebar (st.file_uploader for .json files, calls load_project on upload, displays warning if referenced .txt files not found)
- [ ] T066 [US5] Add project load warnings in sidebar (if loaded project references missing .txt files, show st.warning listing missing filenames and prompting user to re-upload)

**Checkpoint**: All 5 user stories should be complete and independently testable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T067 [P] Add tooltips and help text to all UI controls (st.help or inline markdown explaining parameters, ranges, physical meaning for spike threshold, baseline params, fitting bounds)
- [ ] T068 [P] Add performance optimization with caching (add @st.cache_data to parse_spectrum, baseline_polynomial, baseline_als, auto_find_peaks functions)
- [ ] T069 [P] Add loading spinners for long operations (st.spinner("Fitting in progress...") around fit_voigt_peaks call, st.spinner("Calculating baseline...") around baseline functions)
- [ ] T070 [P] Add data validation warnings (if spectrum Y is all zeros, show st.error("Spectrum appears flat or empty; cannot process"), if two peaks within 2×FWHM, show st.warning("Peaks may overlap excessively"))
- [ ] T071 [P] Add edge case handling for single-peak spectra (ensure auto_find_peaks detects at least 1 peak, fitting works with N=1 peak without errors)
- [ ] T072 [P] Add edge case handling for very noisy spectra (if spike threshold <5.0, show st.info suggesting user may remove legitimate peaks)
- [ ] T073 [P] Implement plot performance optimization (if spectrum >20k points, show st.warning about potential slow rendering, optionally downsample for plotting only while keeping full resolution for fitting)
- [ ] T074 Code cleanup and formatting (run black on all Python files, ensure consistent style)
- [ ] T075 Add type hints to all functions (mypy compliance, NumPy-style type hints for arrays)
- [ ] T076 [P] Create fixture spectra for manual testing in tests/fixtures/sample_raman.txt (3 Gaussian peaks + noise + 2 spikes, typical D/G/2D Raman bands)
- [ ] T077 [P] Create fixture spectra for manual testing in tests/fixtures/sample_pl.txt (2 overlapping peaks + exponential fluorescence background)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses US1's baseline-corrected data but can be tested with pre-cleaned fixtures
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses US2's fit results but can be tested with pre-fitted fixtures
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Enhances US1-3 with multi-file support but each story independently testable
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Saves/loads state from all stories but independently testable

### Within Each User Story

- Tasks marked [P] within a story can run in parallel (different files)
- UI tasks (in src/ui/) typically depend on corresponding processing tasks (in src/processing/) being complete
- Plotter updates depend on data model classes being defined
- Wire-up tasks (in app.py) must be last within each story phase

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004, T005, T006)
- All Foundational data model tasks can run in parallel (T008-T014)
- Within each user story, all tasks marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members after Foundational phase

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together (no dependencies between them):
T018: "Implement modified Z-score de-spiking in despiking.py"
T019: "Implement polynomial baseline in baseline.py"
T020: "Implement ALS baseline in baseline.py"

# After processing algorithms done, launch UI components together:
T021: "Create preprocess_tab.py"
T022: "Add de-spiking UI in preprocess_tab"
T023: "Add baseline correction UI in preprocess_tab"
T024: "Add Reset to Raw button"
T025: "Create basic plotter in plotter.py"

# Final integration (must be sequential after UI complete):
T028: "Wire up preprocess tab in app.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all processing and data model enhancements together:
T029: "Implement auto-bounds calculation in PeakDefinition"
T030: "Implement auto-find peaks in fitting.py"

# After T031 (core fitting) done, launch UI components:
T033: "Create fit_tab.py"
T034: "Add editable peak table"
T035: "Add Auto-Find Peaks button"
T036: "Add Advanced mode checkbox"
T037: "Add Run Fit button"

# Final integration:
T041: "Wire up fit tab in app.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (T018-T028)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Upload sample_raman.txt
   - Remove spikes with threshold 6.0
   - Apply polynomial baseline degree 3
   - Verify corrected spectrum displayed
   - Verify Reset to Raw works
5. Demo/deploy if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (T018-T028) → Test independently → **Deploy/Demo (MVP!)**
3. Add User Story 2 (T029-T041) → Test independently → Deploy/Demo (now with fitting)
4. Add User Story 3 (T042-T050) → Test independently → Deploy/Demo (now with export)
5. Add User Story 4 (T051-T058) → Test independently → Deploy/Demo (now with batch loading)
6. Add User Story 5 (T059-T066) → Test independently → Deploy/Demo (now with project persistence)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T017)
2. Once Foundational is done:
   - Developer A: User Story 1 (T018-T028)
   - Developer B: User Story 2 (T029-T041)
   - Developer C: User Story 3 (T042-T050)
3. Stories complete and integrate independently
4. Merge in priority order (P1 → P2 → P3) for staged releases

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- No test tasks included (not explicitly requested in specification; constitution mandates TDD but doesn't require test tasks in task list)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
