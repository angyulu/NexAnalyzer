# Design: Single-Page UI Architecture

## Context

SpectralFit currently uses a tab-based workflow (`st.tabs(["Pre-process", "Fit Peaks", "Export"])`) where each stage has isolated UI and plotting. This PRD (v2.2) requires consolidating into a single-page, three-panel layout with unified plotting and accordion-based workflow orchestration.

**Constraints:**
- Streamlit limitations: Limited CSS control, no native accordion widget (must simulate with `st.expander`)
- Session state management: Must track per-file status across multiple processing stages
- Backward compatibility: v2.1 project JSON files must load without breaking
- Performance: Plot updates must remain responsive (<100ms) with up to 50,000 data points

**Stakeholders:**
- Research scientists (primary users): Need visual workflow guidance and quick status checks
- Lab technicians: Require mobile access for basic monitoring
- Developers: Must maintain separation of concerns and testability

## Goals / Non-Goals

**Goals:**
1. Single-page layout with three panels (file list | plot | controls) on desktop
2. Unified Plotly figure supporting 5+ toggleable layers (raw, de-spiked, baseline-corrected, fit total, components)
3. Accordion workflow with visual progress (status badges) and auto-expand on completion
4. Stale fit detection when preprocessing changes invalidate existing fits
5. Responsive mobile layout (stacked: files → controls → plot)
6. Preserve v2.1 real-time baseline preview on unified plot

**Non-Goals:**
- Multi-spectrum batch processing UI (still single-file focus per session state)
- Dark mode or theme customization (out of scope for v2.2)
- Undo/redo functionality (not requested in PRD)
- Drag-and-drop file reordering (nice-to-have, deferred)

## Decisions

### D1: Layout Implementation Strategy

**Decision:** Use `st.columns([1, 2.5, 1.5])` for desktop, detect viewport width via JavaScript + session state flag for mobile stacking.

**Rationale:**
- Streamlit's native column API provides predictable horizontal layout
- Proportions (20% / 50% / 30%) match PRD requirements (LR-1)
- Mobile detection: Inject minimal `<script>` tag to set `st.session_state['is_mobile']` based on `window.innerWidth < 1024`
- Alternative considered: CSS-only responsive grid → Rejected due to Streamlit's limited CSS injection support

**Trade-offs:**
- ✅ Simple, maintainable Streamlit idiom
- ❌ Viewport detection requires JavaScript injection (slight complexity)
- ❌ Fixed proportions (not user-resizable) but acceptable per PRD

### D2: Unified Plot Architecture

**Decision:** Single Plotly `go.Figure()` with named traces, managed via `update_traces(visible=...)` for layer toggles.

**Trace schema:**
```python
{
    "raw": scatter trace (blue, markers),
    "despiked": scatter trace (orange, line),
    "baseline_preview": scatter trace (red, dash),
    "corrected_preview": scatter trace (green, line),
    "baseline_corrected": scatter trace (purple, line),
    "fit_total": scatter trace (black, line),
    "component_1": scatter trace (gray, dash),
    "component_2": scatter trace (gray, dash),
    ...
}
```

**Visibility logic:**
- Default on load: Show `raw` only
- After despike: Show `despiked`, hide `raw`
- During baseline preview: Show `baseline_preview` + `corrected_preview` overlaid on current data
- After baseline correction: Show `baseline_corrected`, hide previews
- After fit: Show `baseline_corrected` + `fit_total`, optionally show components

**Rationale:**
- Plotly's trace-based model natively supports show/hide without recomputation
- Named traces enable clear checkbox → visibility mapping
- Alternative considered: Multiple separate plots → Rejected, violates PRD's "single unified plot" (FR-C1)

**Trade-offs:**
- ✅ No plot recreation overhead (fast toggles)
- ✅ Consistent zoom/pan state across layers
- ❌ Trace count scales with peak count (fit components), but typical spectra have 2-10 peaks (acceptable)

### D3: Status Tracking Model

**Decision:** Extend `SpectrumFile` dataclass with status flags; update via helper functions after each processing step.

**Schema extension:**
```python
@dataclass
class SpectrumFile:
    # ... existing fields ...

    # v2.2 status tracking
    despike_done: bool = False
    baseline_done: bool = False
    fit_done: bool = False
    fit_stale: bool = False  # True if preprocessing changed after fit
    last_preprocessing_hash: Optional[str] = None  # SHA256 of (despike + baseline params)
```

**Badge computation logic:**
```python
def compute_badge_state(spectrum: SpectrumFile, stage: str) -> str:
    """Returns: 'not_run' | 'done' | 'warning'"""
    if stage == "despike":
        return "done" if spectrum.despike_done else "not_run"
    elif stage == "baseline":
        return "done" if spectrum.baseline_done else "not_run"
    elif stage == "fit":
        if spectrum.fit_stale:
            return "warning"
        return "done" if spectrum.fit_done else "not_run"
```

**Stale fit detection:**
- Compute hash of `(despike_params, baseline_params)` after each preprocessing step
- Compare to `last_preprocessing_hash` at fit time
- If mismatch: Set `fit_stale = True`, show warning badge

**Rationale:**
- Dataclass extension keeps status co-located with processing data
- Hash-based staleness detection is simple and robust (no manual dependency tracking)
- Alternative considered: Event log / state machine → Rejected as over-engineered for this scope

**Trade-offs:**
- ✅ Straightforward to persist in project JSON (just add new fields with defaults)
- ✅ Clear boolean flags for UI logic
- ❌ Requires updating SpectrumFile throughout UI code (but well-scoped)

### D4: Accordion Workflow Implementation

**Decision:** Use `st.expander()` for each section, store `expanded_section` in session state, auto-expand next section on "Run" button success.

**Section structure (right panel):**
```python
sections = [
    ("processing_range", "Processing Range"),
    ("despike", "De-spiking"),
    ("baseline", "Baseline Correction"),
    ("peak_fit", "Peak Fitting"),
    ("export", "Export")
]

for section_id, section_title in sections:
    is_expanded = st.session_state.get('expanded_section') == section_id
    with st.expander(section_title, expanded=is_expanded):
        render_section_controls(section_id)
        if st.button(f"Run {section_title}", key=f"run_{section_id}"):
            success = execute_processing_step(section_id)
            if success:
                mark_section_done(section_id)
                expand_next_section(section_id)
```

**Sequential access rules:**
- Despike: Always enabled
- Baseline: Always enabled (can skip despike if desired)
- Peak Fit: Enabled only if `baseline_done == True`
- Export: Always enabled (but warns if any file has `fit_done == False`)

**Rationale:**
- Streamlit's `st.expander()` provides native accordion behavior
- Session state tracking enables auto-expand without full page reload
- Alternative considered: Custom collapsible divs via HTML/CSS → Rejected due to Streamlit reactivity issues

**Trade-offs:**
- ✅ Native Streamlit widget (minimal custom code)
- ✅ Keyboard accessibility built-in
- ❌ All expanders rendered (no lazy loading), but 5 sections is acceptable

### D5: Clickable Badge Navigation

**Decision:** Use `st.button()` for badges in file cards, set `st.session_state['expanded_section']` and `st.session_state['scroll_target']` on click.

**Implementation sketch:**
```python
# In left panel file card
if st.button("Despike", key=f"badge_despike_{filename}"):
    st.session_state['expanded_section'] = 'despike'
    st.session_state['scroll_target'] = 'despike'
    st.rerun()

# In right panel
if st.session_state.get('scroll_target') == 'despike':
    st.markdown('<div id="despike-anchor"></div>', unsafe_allow_html=True)
    st.session_state['scroll_target'] = None  # Clear after rendering
```

**Rationale:**
- Streamlit buttons trigger rerun with updated session state
- Anchor tags enable scroll targeting (though Streamlit doesn't support `scrollIntoView()` directly)
- Alternative considered: URL hash fragments → Rejected, Streamlit doesn't expose hash routing

**Trade-offs:**
- ✅ Simple button-based navigation
- ❌ No smooth scrolling (Streamlit limitation), but acceptable for UX
- ❌ Requires manual scroll targeting via HTML anchors

## Risks / Trade-offs

### R1: Streamlit Layout Limitations

**Risk:** `st.columns()` doesn't support user-resizable panels or CSS grid.

**Mitigation:**
- Accept fixed proportions (20/50/30) as designed in PRD
- Future enhancement (v2.3+): Consider migration to Dash/Plotly Dash if resizable panels become critical

### R2: Performance with Large Trace Counts

**Risk:** Plotly figures with 10+ traces (5 base + 5-10 fit components) may lag on updates.

**Mitigation:**
- Lazy component rendering: Only add component traces if "Show Components" checkbox enabled
- Downsample raw data traces if >50k points (existing downsampling logic in visualization module)
- Benchmark with pathological case (10 peaks × 50k points) during Phase 2 testing

### R3: Mobile Layout Usability

**Risk:** Stacked layout (Files → Controls → Plot) may require excessive scrolling on small screens.

**Mitigation:**
- PRD explicitly defines stacking order (FR-L2: Files top, Plot bottom)
- Add "Jump to Plot" quick-link button at top of controls panel on mobile
- Accept that mobile is a monitoring view, not a primary workflow (per stakeholder priorities)

### R4: Backward Compatibility Edge Cases

**Risk:** v2.1 project files with missing status fields could break deserialization.

**Mitigation:**
- Add default values in `SpectrumFile.__post_init__()`:
  ```python
  if not hasattr(self, 'despike_done'):
      self.despike_done = False
  # ... repeat for all new fields
  ```
- Schema migration test: Load 10 v2.1 sample projects during Phase 4 QA

## Migration Plan

### Phase 1: Core Layout (Week 1)
1. Replace `st.tabs()` with `st.columns([1, 2.5, 1.5])` in `app.py`
2. Stub out three panels: Left (file cards), Center (empty plot div), Right (section headers)
3. Add viewport width detection script and `is_mobile` session state flag
4. Test desktop/mobile layout switching manually

### Phase 2: Unified Plot (Week 2)
1. Create `src/visualization/unified_plot.py` with `render_unified_plot(spectrum, layer_config)`
2. Migrate raw/despiked/corrected plotting logic from tab modules
3. Implement layer visibility checkboxes in right panel "View Options" subsection
4. Integrate v2.1 baseline preview traces (red dash + green line)
5. Add X-range visual indicators (vertical spans)

### Phase 3: Accordion Workflow (Week 3)
1. Implement `st.expander()` sections in right panel with `expanded_section` state tracking
2. Add "Run" buttons with success → auto-expand logic
3. Update `SpectrumFile` schema with status flags
4. Implement badge rendering in left panel file cards
5. Wire badge click → section expand/scroll

### Phase 4: State Management & Polish (Week 4)
1. Implement stale fit detection (hash-based preprocessing tracking)
2. Add export dialog with file selection options
3. Migrate v2.1 project JSON compatibility layer
4. Mobile layout QA and scroll target polishing
5. Load testing with 10 files × 10 peaks each

### Rollback Plan

If critical issues arise post-deployment:
1. Revert `app.py` to v2.1 tab structure via Git
2. Maintain v2.2 branch for further refinement
3. No data loss risk (project JSON format is backward-compatible)

## Open Questions

1. **Scroll behavior clarification:** Should badge clicks trigger hard scroll-to-top of section, or is expansion + manual scroll acceptable? (Assuming manual scroll per Streamlit constraints)

2. **Error messaging placement:** Global alert bar vs inline per-section? PRD specifies both (FR-R4); confirm priority if conflict.

3. **Component visibility default:** Should "Show Components" default to ON or OFF after fit? (Recommending OFF to reduce clutter, but seeking user preference)

4. **Mobile breakpoint:** PRD suggests <1024px for stacking. Confirm this matches target device set (tablets in landscape?).
