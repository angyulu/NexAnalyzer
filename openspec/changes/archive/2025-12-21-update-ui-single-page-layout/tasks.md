# Implementation Tasks: Single-Page UI Layout

## Phase 1: Core Layout Infrastructure (Week 1)

### 1.1 Desktop Layout Structure
- [ ] 1.1.1 Replace `st.tabs()` with `st.columns([1, 2.5, 1.5])` in `app.py`
- [ ] 1.1.2 Create placeholder divs for three panels: file list (left), plot (center), controls (right)
- [ ] 1.1.3 Verify column proportions render as 20% / 50% / 30% on standard desktop viewport

### 1.2 Mobile Layout Detection
- [ ] 1.2.1 Add JavaScript viewport width detection script to `app.py` (inject via `st.markdown(unsafe_allow_html=True)`)
- [ ] 1.2.2 Add `is_mobile` flag to session state (set via JS callback or server-side user-agent detection)
- [ ] 1.2.3 Implement conditional rendering: columns for desktop, vertical stack for mobile (<1024px)
- [ ] 1.2.4 Test mobile layout manually on small viewport (use browser dev tools)

### 1.3 Left Panel Skeleton
- [ ] 1.3.1 Create `src/ui/file_panel.py` module for left panel rendering
- [ ] 1.3.2 Render file list with placeholder cards (filename only, no badges yet)
- [ ] 1.3.3 Migrate mode chip display from existing sidebar logic
- [ ] 1.3.4 Add file selection logic (click card to set `current_file`)

### 1.4 Right Panel Skeleton
- [ ] 1.4.1 Create `src/ui/control_panel.py` module for right panel rendering
- [ ] 1.4.2 Add five `st.expander()` placeholders with section titles: Processing Range, De-spiking, Baseline, Peak Fit, Export
- [ ] 1.4.3 Verify expanders collapse/expand correctly
- [ ] 1.4.4 Add `expanded_section` to session state for tracking active section

### 1.5 Center Panel Placeholder
- [ ] 1.5.1 Create `src/visualization/unified_plot.py` module
- [ ] 1.5.2 Render empty Plotly figure in center panel with placeholder text "Plot will appear here"
- [ ] 1.5.3 Verify plot container scales to 50% column width

## Phase 2: Unified Plot Implementation (Week 2)

### 2.1 Multi-Layer Plot Architecture
- [ ] 2.1.1 Design trace schema with named layers: `raw`, `despiked`, `baseline_preview`, `corrected_preview`, `baseline_corrected`, `fit_total`, `component_N`
- [ ] 2.1.2 Implement `create_unified_figure(spectrum: SpectrumFile, layer_config: dict) -> go.Figure` function
- [ ] 2.1.3 Add `add_layer(fig, layer_name, x_data, y_data, style_config)` helper function
- [ ] 2.1.4 Migrate raw data plotting logic from `preprocess_tab.py`

### 2.2 Layer Visibility Controls
- [ ] 2.2.1 Add "View Options" subsection in right panel (above Processing Range section)
- [ ] 2.2.2 Create checkboxes: "Show Raw", "Show De-spiked", "Show Baseline-corrected", "Show Fit", "Show Components"
- [ ] 2.2.3 Implement `update_layer_visibility(fig, layer_name, visible: bool)` using Plotly `update_traces()`
- [ ] 2.2.4 Wire checkbox changes to update plot without full rerender

### 2.3 Default Visibility Logic
- [ ] 2.3.1 Implement `compute_default_visibility(spectrum: SpectrumFile) -> dict` based on processing stage
- [ ] 2.3.2 Auto-hide raw layer when de-spiked data exists
- [ ] 2.3.3 Auto-show baseline-corrected layer when baseline step completes
- [ ] 2.3.4 Auto-show fit total when fitting completes (components hidden by default)

### 2.4 Real-Time Baseline Preview Integration
- [ ] 2.4.1 Migrate v2.1 baseline preview logic into unified plot
- [ ] 2.4.2 Add `baseline_preview` trace (red dashed line) and `corrected_preview` trace (green solid line)
- [ ] 2.4.3 Trigger preview update on baseline parameter change (polynomial degree, ALS lambda slider)
- [ ] 2.4.4 Remove preview traces when "Run Baseline Correction" button clicked
- [ ] 2.4.5 Verify preview overlays do not hide current data layer

### 2.5 X-Range Visual Indicators
- [ ] 2.5.1 Add vertical span annotations to plot for X-range boundaries (from v2.1 FR-13)
- [ ] 2.5.2 Update span positions when user adjusts X-min/X-max controls
- [ ] 2.5.3 Ensure spans render consistently across all layers

### 2.6 Plot Performance Testing
- [ ] 2.6.1 Test plot rendering with 50,000 data points (typical max spectrum size)
- [ ] 2.6.2 Benchmark layer visibility toggle latency (target: <100ms)
- [ ] 2.6.3 Test with pathological case: 10 peaks (10 component traces) × 50k points

## Phase 3: Workflow Orchestration (Week 3)

### 3.1 Session State Schema Extension
- [ ] 3.1.1 Add fields to `SpectrumFile` dataclass: `despike_done: bool`, `baseline_done: bool`, `fit_done: bool`, `fit_stale: bool`, `last_preprocessing_hash: str`
- [ ] 3.1.2 Initialize new fields with default values (`False`, `None`) in `__post_init__()`
- [ ] 3.1.3 Update project JSON serialization to include new fields
- [ ] 3.1.4 Add backward compatibility: handle v2.1 project files missing new fields

### 3.2 Status Badge Rendering
- [ ] 3.2.1 Implement `render_status_badge(badge_type: str, state: str, filename: str)` in `file_panel.py`
- [ ] 3.2.2 Create badge state styles: "not_run" (gray), "done" (green + checkmark), "warning" (yellow + !)
- [ ] 3.2.3 Render three badges per file card: Despike, Baseline, Fit
- [ ] 3.2.4 Implement `compute_badge_state(spectrum, stage)` logic based on `*_done` and `*_stale` flags

### 3.3 Badge Click Navigation
- [ ] 3.3.1 Make each badge a `st.button()` with unique key (e.g., `badge_despike_{filename}`)
- [ ] 3.3.2 On badge click: set `st.session_state['expanded_section']` to target section
- [ ] 3.3.3 On badge click: set `st.session_state['scroll_target']` (for future scroll enhancement)
- [ ] 3.3.4 Trigger `st.rerun()` to apply section expansion
- [ ] 3.3.5 Show tooltip "Complete previous steps first" when clicking disabled Fit badge (if baseline not done)

### 3.4 Accordion Section Migration
- [ ] 3.4.1 Migrate Processing Range controls from `preprocess_tab.py` to first expander in `control_panel.py`
- [ ] 3.4.2 Migrate De-spiking controls to second expander
- [ ] 3.4.3 Migrate Baseline Correction controls to third expander
- [ ] 3.4.4 Migrate Peak Fitting controls from `fit_tab.py` to fourth expander
- [ ] 3.4.5 Migrate Export controls from `export_tab.py` to fifth expander

### 3.5 Sequential Access Rules
- [ ] 3.5.1 Implement `is_section_enabled(section_id, spectrum)` helper function
- [ ] 3.5.2 Disable Peak Fit expander if `baseline_done == False` (show note: "Complete baseline correction first")
- [ ] 3.5.3 Always enable Processing Range, De-spiking, Baseline, and Export sections
- [ ] 3.5.4 Allow re-opening completed sections for editing

### 3.6 Section Completion Logic
- [ ] 3.6.1 Add "Run" buttons to each section: "Run Despike", "Run Baseline Correction", "Run Peak Fit"
- [ ] 3.6.2 On successful run: update corresponding `*_done` flag in `SpectrumFile`
- [ ] 3.6.3 On successful run: expand next section via `st.session_state['expanded_section'] = next_section_id`
- [ ] 3.6.4 On failed run: keep current section expanded, show inline error message
- [ ] 3.6.5 Add success banner with auto-dismiss (3 seconds) using `st.success()` or custom toast

### 3.7 Inline Error Handling
- [ ] 3.7.1 Implement `show_inline_error(message: str, section: str)` function
- [ ] 3.7.2 Display red error box at top of section on parameter validation failure
- [ ] 3.7.3 Add error icon to corresponding badge in file card when section error occurs
- [ ] 3.7.4 Implement global alert bar for critical errors (file load failure) using `st.error()` at top of `app.py`

### 3.8 Reset and Invalidation
- [ ] 3.8.1 Add "Reset to Raw" button in Processing Range section
- [ ] 3.8.2 On reset: clear `despike_done`, `baseline_done`, `fit_done` flags
- [ ] 3.8.3 On reset: clear processed data arrays (de-spiked, corrected, fit results) in `SpectrumFile`
- [ ] 3.8.4 On reset: update plot to show only raw layer
- [ ] 3.8.5 On reset: show message in Peak Fit section if fit was cleared

### 3.9 Stale Fit Detection
- [ ] 3.9.1 Implement `compute_preprocessing_hash(spectrum)` using hashlib.sha256 on (despike_params, baseline_params)
- [ ] 3.9.2 Update `last_preprocessing_hash` after each Despike or Baseline run
- [ ] 3.9.3 On preprocessing parameter change: compare hash, set `fit_stale = True` if mismatch and fit exists
- [ ] 3.9.4 Update Fit badge to "warning" state when `fit_stale == True`
- [ ] 3.9.5 Show yellow note in Peak Fit section: "Preprocessing changed; fit no longer matches current data"
- [ ] 3.9.6 Clear `fit_stale` flag when user re-runs peak fitting

## Phase 4: Integration, State Management & Polish (Week 4)

### 4.1 Export Dialog Implementation
- [ ] 4.1.1 Create export dialog with three radio button options: "Export current file", "Export all processed files", "Export only files with successful fit"
- [ ] 4.1.2 Implement file filtering logic for each export option
- [ ] 4.1.3 Add stale fit detection in export: scan selected files for `fit_stale == True`
- [ ] 4.1.4 Show warning dialog if stale fits detected: "Some files require refitting; stale fits may be excluded"
- [ ] 4.1.5 Implement "Exclude stale fits and continue" logic
- [ ] 4.1.6 Display summary message after export: "Exported X files (Y files skipped due to stale fits)"

### 4.2 Project Persistence Compatibility
- [ ] 4.2.1 Test loading v2.1 project JSON files (should auto-populate new fields with defaults)
- [ ] 4.2.2 Test saving v2.2 project JSON files with new status fields
- [ ] 4.2.3 Verify round-trip: save v2.2 project → reload → verify all status flags preserved
- [ ] 4.2.4 Add schema migration test: load 5 sample v2.1 projects, verify no errors

### 4.3 Mobile Layout QA
- [ ] 4.3.1 Test stacked layout on <1024px viewport (use Chrome DevTools responsive mode)
- [ ] 4.3.2 Verify stacking order: File list → Controls → Plot
- [ ] 4.3.3 Add "Jump to Plot" quick-link button at top of control panel (mobile only)
- [ ] 4.3.4 Verify all accordion sections function correctly in stacked mode
- [ ] 4.3.5 Test file card selection and badge navigation on mobile

### 4.4 Plot State Synchronization
- [ ] 4.4.1 Ensure plot updates when switching between files in left panel
- [ ] 4.4.2 Preserve zoom/pan state per file (store in `SpectrumFile` or session state)
- [ ] 4.4.3 Verify layer visibility checkboxes sync with current file's processing state
- [ ] 4.4.4 Test rapid file switching (10 files, quick clicks) for race conditions

### 4.5 UI Polish and Accessibility
- [ ] 4.5.1 Add loading spinners during processing steps (despike, baseline, fit)
- [ ] 4.5.2 Ensure all buttons have clear labels and tooltips
- [ ] 4.5.3 Verify keyboard navigation works for all expanders and checkboxes
- [ ] 4.5.4 Test screen reader compatibility (basic: section headings, button labels)
- [ ] 4.5.5 Add hover states for file cards and badges

### 4.6 Performance and Load Testing
- [ ] 4.6.1 Load test: 10 files × 10 peaks each, verify UI remains responsive
- [ ] 4.6.2 Measure initial page load time with 10 files pre-loaded (target: <2 seconds)
- [ ] 4.6.3 Profile session state size with large projects (ensure <10MB for 20 files)
- [ ] 4.6.4 Test plot rendering performance with all layers visible + 10 components

### 4.7 Cleanup and Code Organization
- [ ] 4.7.1 Remove deprecated tab modules: `preprocess_tab.py`, `fit_tab.py`, `export_tab.py` (or archive if needed for reference)
- [ ] 4.7.2 Consolidate session state helpers into `session_state.py` (add badge state functions)
- [ ] 4.7.3 Add docstrings to all new functions (Google style)
- [ ] 4.7.4 Run linter (flake8 or black) on modified files
- [ ] 4.7.5 Update `app.py` footer version string: "SpectralFit v2.2"

### 4.8 Documentation and Migration Guide
- [ ] 4.8.1 Update README with v2.2 UI overview and screenshots
- [ ] 4.8.2 Create migration guide for v2.1 → v2.2 (UI changes, project file compatibility)
- [ ] 4.8.3 Update quickstart guide with new accordion workflow instructions
- [ ] 4.8.4 Add troubleshooting section for common issues (e.g., stale fit warnings)

### 4.9 Final QA and User Testing
- [ ] 4.9.1 End-to-end test: Load file → Despike → Baseline → Fit → Export (verify all badges update)
- [ ] 4.9.2 Test reset workflow: Complete all steps → Reset → Verify fit invalidated
- [ ] 4.9.3 Test stale fit workflow: Fit → Change baseline params → Verify warning → Refit → Verify cleared
- [ ] 4.9.4 Test export with stale fits: Verify warning dialog and exclusion logic
- [ ] 4.9.5 User acceptance testing: 2-3 target users try new UI, collect feedback

## Post-Implementation Tasks

### 5.1 Deployment Preparation
- [ ] 5.1.1 Create v2.2 release branch from main
- [ ] 5.1.2 Tag release: `git tag -a v2.2.0 -m "Single-page UI layout with workflow orchestration"`
- [ ] 5.1.3 Update CHANGELOG.md with v2.2 release notes
- [ ] 5.1.4 Build and test Docker image (if applicable)

### 5.2 Rollback Plan Documentation
- [ ] 5.2.1 Document Git rollback procedure: `git revert <commit>` for v2.2 UI changes
- [ ] 5.2.2 Verify v2.1 branch still builds and runs correctly (fallback option)
- [ ] 5.2.3 Archive v2.1 tab-based UI code in separate branch for reference

## Dependencies and Parallelization Notes

**Sequential dependencies:**
- Phase 1 must complete before Phase 2 (need layout skeleton before plot integration)
- Phase 2 must complete before Phase 3 (need unified plot before workflow orchestration)
- Phase 3.1 (schema extension) must complete before Phase 3.2 (badge rendering)

**Parallelizable work:**
- Phase 1.3 (left panel) and Phase 1.4 (right panel) can be developed in parallel
- Phase 2.2 (visibility controls) and Phase 2.4 (preview integration) can overlap
- Phase 3.4 (section migration) subsections can be split across multiple developers
- Phase 4.3 (mobile QA) and Phase 4.5 (UI polish) can be done concurrently

**External dependencies:**
- None (all work contained within SpectralFit codebase)
- Streamlit version: Ensure >=1.28 for stable `st.expander()` and `st.columns()` behavior
