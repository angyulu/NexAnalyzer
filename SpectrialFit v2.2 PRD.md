# SpectralFit UI Upgrade PRD – Single-Page, 3-Panel Layout

**Version:** 2.2 (UI Upgrade)  
**Base Version:** 2.1  
**Date:** December 20, 2025  
**Status:** Ready for Development  
**Scope:** UI/UX only – reuse existing processing and export logic

---

## Objective

Transform the current tab-based interface into a **single-page, three-panel layout** that supports a linear, guided workflow: file selection → pre-process (despike + baseline) → peak fitting → export, all on one page.

---

## High-Level Layout

### LR-1: Three-Panel Layout (Desktop)

**Requirement**  
The main page is divided horizontally into three panels:

- **Left panel (20% width):** File list & status  
- **Center panel (50% width):** Unified Plotly spectrum plot  
- **Right panel (30% width):** All controls (Pre-process, Peak Fit, Export) in a single scrollable panel

**Behavior**

- Implement with `st.columns([1, 2.5, 1.5])` or equivalent proportion in Streamlit.
- Only **one** main page; no Pre-process / Fit / Export tabs.

### LR-2: Mobile / Small Screen Layout

**Requirement**  
On small viewports, panels stack vertically:

- Top: File list  
- Middle: Controls  
- Bottom: Plot  

**Behavior**

- For widths below a defined breakpoint (e.g., < 1024 px), use stacked layout: Files → Controls → Plot.
- All functionality remains available; only order and stacking change.

---

## Left Panel – File List & Status

### FR-L1: File Cards with Status Badges

**Requirement**  
Each loaded file appears as a **card** with mode and processing status.

**Card Content**

- Filename  
- Mode chip: Raman / PL (from existing auto-detection logic)  
- Status badges (3):  
  - Despike  
  - Baseline  
  - Fit  

**Badge States**

- **Default:** Gray border, "Not run"  
- **Done:** Green with ✓  
- **Warning:** Yellow border with ! if there is a known issue (e.g., fit stale)  

**Completion Rules**

- A step is marked **Done** if:
  - It has **non-default settings** and has successfully executed at least once.  
- If the user clicks "Reset to Raw" or fully reverts that stage:
  - Clear the corresponding Done badge.  

### FR-L2: Clickable Badges to Jump to Section

**Requirement**  
Badges act as navigation shortcuts.

**Behavior**

- Clicking "Despike" badge:
  - Scrolls / focuses the right panel on the Despike section (and expands it if collapsed).  
- Clicking "Baseline" badge:
  - Focuses Baseline section.  
- Clicking "Fit" badge:
  - Focuses Peak Fit section.  
- If that section is disabled due to workflow rules (e.g., Fit before Baseline), show a small tooltip: "Complete previous steps first."

### FR-L3: Error Indicators

**Requirement**  
Errors should be visible per file.

**Behavior**

- If a step encounters an error (e.g., invalid baseline parameters):
  - Show inline error in the right panel section (see FR-R4).  
  - Add a small warning icon to the corresponding badge in the file card.  
- For critical file-level errors (e.g., parse failure), mark the whole card with a red border and show "Error" label.

---

## Center Panel – Unified Plot

### FR-C1: Single Plot for All Stages

**Requirement**  
Despike, baseline correction, and peak fitting all use **one unified Plotly plot**.

**Traces (possible layers)**

- Raw data  
- De-spiked data  
- Baseline-corrected data  
- Fit result (total curve)  
- Individual components (optional: one trace per peak)  

### FR-C2: Default Visibility Rules

**Requirement**  
After each processing step, the most recent result is emphasized.

**Behavior**

- Raw:
  - Visible at initial load.  
- After Despike:
  - **Default visible:** De-spiked data.  
  - Raw can be toggled back on.  
- After Baseline:
  - **Default visible:** Baseline-corrected data.  
  - Raw / De-spiked can be toggled on via controls.  
- After Fit:
  - **Default visible:** Baseline-corrected data + Fit total curve.  
  - Components visibility controlled via legend/checkboxes.  

### FR-C3: Layer Toggles in Right Panel

**Requirement**  
Visibility is controlled via simple checkboxes in the right panel (in a "View options" subsection).

**Behavior**

- Checkboxes:
  - `Show Raw`  
  - `Show De-spiked`  
  - `Show Baseline-corrected`  
  - `Show Fit`  
  - `Show Components`  
- Toggling these updates the Plotly trace visibility without recomputation.

### FR-C4: Real-Time Baseline Preview

**Requirement**  
Preserve v2.1 real-time baseline preview (red dashed baseline + green corrected overlay) on the unified plot.

**Behavior**

- When user adjusts baseline parameters:
  - Preview baseline (red dashed) and preview corrected (green) overlaid on current data.
- Preview uses cached results as in v2.1.
- Preview disappears once user clicks "Run Baseline Correction"; final corrected data replaces previous processed layer.

---

## Right Panel – Single Control Panel

All processing steps (Processing Range, Despike, Baseline, Peak Fit, Export) live in the **same panel**, organized as collapsible sections (accordion style).

### FR-R1: Accordion Sections & Order

**Sections (top to bottom):**

1. Processing Range  
2. De-spiking  
3. Baseline Correction  
4. Peak Fitting  
5. Export  

**Accordion Behavior**

- Only 1–2 sections expanded at a time for clarity.  
- Completed sections can be re-opened in "Edit" mode.  
- Sections beyond the current step are disabled or show a note if dependencies are not met.

### FR-R2: Sequential with Edit (Workflow Rules)

**Requirement**  
The workflow is guided but editable.

**Rules**

- User can open sections in order: 1 → 2 → 3 → 4 → 5  
- Peak Fitting (4) is disabled until Baseline (3) has been run at least once.  
- Export (5) is always accessible but shows warnings if some files haven't completed Peak Fit.  
- Re-opening an earlier section (Edit):
  - Allowed at any time.  
  - May invalidate later results (see FR-R6).

### FR-R3: Section Completion & Auto-Expand

**Requirement**  
Smooth transition between steps without disruptive scrolling.

**Behavior**

- Each section has a primary "Run …" button (e.g., "Run Despike", "Run Baseline Correction", "Run Peak Fit").  
- Upon **successful run**:
  - Mark that step as Done (update badge in left panel).  
  - Automatically **expand the next section** (but do not auto-scroll the viewport).  
  - Optionally show a brief success banner within the section.  
- On failure:
  - Do NOT expand next section.  
  - Show inline error message (FR-R4).

### FR-R4: Inline Error & Global Alerts

**Requirement**  
Clear, non-technical errors.

**Behavior**

- Inline:
  - Error shown at top of current section in red text, with suggestions.  
- Left panel:
  - Add warning icon to the corresponding step badge.  
- Global:
  - For critical errors (file load failure, project load error), show a global alert bar at top of the page.

### FR-R5: Reset Behavior

**Requirement**  
Reset is consistent and safe.

**Behavior**

- "Reset to Raw" in the Pre-process area:
  - Clears Despike and Baseline results for that file.  
  - Clears associated status badges (Despike, Baseline).  
  - **Invalidates Peak Fit** for that file:
    - Clear Fit badge.  
    - Show message in Peak Fit section: "Preprocessing changed; previous fit cleared. Please run fitting again."  
- Plot is updated to show only raw data.

### FR-R6: Editing Earlier Steps After Fitting

**Requirement**  
Fits must reflect current preprocessing.

**Behavior**

- If user changes Despike or Baseline after a fit was already run:
  - Existing fit is marked as **stale**:
    - Left panel Fit badge shows warning icon or "Refit needed".  
    - Peak Fit section shows yellow note: "Preprocessing changed; fit no longer matches current data."  
  - Export:
    - By default, stale fits should either be excluded or trigger a warning when exporting.  
- A new successful fit run replaces stale status and updates badges.

---

## Export Section (Right Panel, Bottom)

### FR-E1: Single Export Entry Point

**Requirement**  
Export controls live at the bottom of the right panel as one unified section.

**Controls**

- Button: `Export…`  

**Export Dialog Options**

- `Export current file`  
- `Export all processed files`  
- `Export only files with successful fit`  

**Behavior**

- Uses existing export logic and formats (Master CSV, single-file CSV, PNG/HTML).  
- If any selected file has stale fits:
  - Show warning: "Some files require refitting; stale fits may be excluded from export."

---

## Non-Functional Requirements

### NFR-1: Performance

- Plot updates (layer visibility, section completion) should remain responsive with typical spectra sizes as in v2.1 (up to ~10⁴–5×10⁴ points).  
- Accordion expansion should not trigger heavy recomputation; only the relevant section logic reruns.

### NFR-2: State Persistence

- Per-file:
  - Status of Despike/Baseline/Fit  
  - X-range settings  
  - Flags indicating stale fits  
- Global:
  - Last-opened section in right panel  
  - Current layout mode (desktop/stacked, if stored)  

State persists within session and through project JSON as extensions of the existing `SpectrumFile` and `ProjectState` models.

---

## Implementation Roadmap

### Phase 1: Core Layout (Week 1)
- Implement 3-column Streamlit layout with correct proportions
- File card UI in left panel with status badges
- Empty center plot container
- Right panel skeleton with section headers

### Phase 2: Unified Plot (Week 2)
- Migrate all plotting to single Plotly figure with multiple traces
- Layer visibility controls
- Integrate real-time preview overlay
- X-range visual indicators

### Phase 3: Accordion Workflow (Week 3)
- Implement expander logic with session state tracking
- Processing Range → De-spiking → Baseline → Peak Fitting → Export
- Progress badges update on section completion
- Clickable badges for navigation

### Phase 4: State Management & Polish (Week 4)
- Unified plot updates based on active processing stage
- Section completion tracking and stale fit detection
- Export dialog with file selection options
- Mobile/stacked layout support

---

## Backward Compatibility

- **v2.1 project files:** Fully compatible; new UI fields added with defaults
- **Existing backend:** No changes to processing algorithms, only UI organization
- **Export formats:** Unchanged from v2.1

---

**Approval:** Ready for implementation  
**Next Step:** Developer review and sprint planning for 4-week delivery cycle
