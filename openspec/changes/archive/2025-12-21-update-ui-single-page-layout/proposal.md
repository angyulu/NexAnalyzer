# Change: Update UI to Single-Page, Three-Panel Layout

## Why

The current tab-based interface (Pre-process → Fit Peaks → Export) hides workflow context and forces users to switch tabs repeatedly to check processing status, view plots, and adjust parameters. This creates cognitive overhead and disrupts the linear analysis workflow. A unified single-page layout will provide:

- **Visual continuity**: See file status, plot, and controls simultaneously without tab switching
- **Guided workflow**: Sequential accordion sections with visual progress tracking via status badges
- **Real-time feedback**: All processing stages visible on one unified plot with layer toggles
- **Mobile support**: Responsive stacked layout for smaller viewports

## What Changes

Transform the current 3-tab interface into a **single-page, three-panel horizontal layout**:

- **Left panel (20% width)**: File list with status badges (Despike, Baseline, Fit) and clickable navigation shortcuts
- **Center panel (50% width)**: Unified Plotly plot showing all processing layers (raw, de-spiked, baseline-corrected, fit) with visibility controls
- **Right panel (30% width)**: Single scrollable control panel with accordion sections (Processing Range → Despike → Baseline → Peak Fit → Export)

**Key behavioral changes:**
- Replace `st.tabs()` with `st.columns([1, 2.5, 1.5])` for desktop layout
- Merge all plotting into one Plotly figure with multiple toggleable traces
- Implement accordion workflow with auto-expand on section completion
- Add per-file status tracking (badge states: Not run / Done / Warning)
- Add stale fit detection when preprocessing changes after fitting
- Support mobile/stacked layout for small viewports (<1024px)

**Preserved from v2.1:**
- Real-time baseline preview (red dashed baseline + green corrected overlay)
- All existing processing algorithms (despike, baseline, fitting, export)
- Project save/load format compatibility
- Mode auto-detection and X-range controls

## Impact

**Affected specs:**
- `ui-layout` (NEW): Three-panel layout requirements and responsive behavior
- `file-management` (NEW): File card UI, status badges, navigation shortcuts
- `plot-visualization` (MODIFIED): Unified plot with multi-layer support and visibility controls
- `workflow-orchestration` (NEW): Accordion sections, completion rules, stale fit detection
- `export` (MODIFIED): Single export entry point at bottom of right panel

**Affected code:**
- `app.py`: Replace tab structure with column layout
- `src/ui/preprocess_tab.py` → Refactor into accordion sections in right panel
- `src/ui/fit_tab.py` → Merge into right panel Peak Fit section
- `src/ui/export_tab.py` → Merge into right panel Export section
- `src/ui/sidebar.py` → Transform into left panel with file cards
- `src/ui/session_state.py`: Add status tracking fields (`despike_done`, `baseline_done`, `fit_done`, `fit_stale`)
- `src/visualization/` (NEW or MODIFIED): Unified plot renderer with layer management
- `src/models/spectrum.py`: Extend `SpectrumFile` with status flags

**User-facing impact:**
- **Breaking UI change**: Users must adapt to new layout (but all functionality preserved)
- **Migration**: v2.1 project files auto-upgrade with default status values
- **Learning curve**: ~5 minutes to understand new accordion workflow vs tabs
- **Performance**: No algorithmic changes; plot updates remain <100ms for typical spectra

**Timeline estimate:** 4 weeks (Phases 1-4 per PRD roadmap)
