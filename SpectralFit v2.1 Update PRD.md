<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# SpectralFit v2.1 Update PRD

**Version:** 2.1
**Base Version:** 2.0
**Date:** December 19, 2025
**Status:** Ready for Development
**Update Type:** Feature Enhancement \& Bug Fix

***

## Update Summary

This release addresses four critical improvements to enhance usability and reliability based on user feedback. The updates focus on intelligent automation, error handling, visual flexibility, and precision processing controls.[^1]

***

## New Features \& Requirements

### FR-12: Auto Mode Detection from Filename

**Priority:** Medium
**Rationale:** Reduces manual clicks for well-organized datasets while maintaining flexibility.[^1]

**Implementation**

- **Detection logic:** Strict prefix matching (case-insensitive)
    - `RM*` → Auto-set to Raman mode[^1]
    - `PL*` → Auto-set to PL mode[^1]
    - Other patterns → No change to current mode

**UI Changes**

- When auto-detection triggers on file load, display dismissible banner: "Mode auto-detected as [Raman/PL] from filename; change manually if incorrect"[^1]
- Banner auto-dismisses after 5 seconds or on user click
- Manual mode toggle always overrides auto-detection

**State Management**

- Auto-detected mode saved in per-file state and project JSON[^1]
- No changes to raw data; only affects units, labels, and fitting bounds[^1]

***

### FR-13: Baseline Error Handling for Negative Y Values

**Priority:** High (Bug Fix)
**Current Issue:** "Baseline correction failed: Y values must be non-negative" error blocks workflow.[^1]

**Solution: Automatic Y-Shift**

- When baseline algorithm encounters negative Y values, automatically apply internal vertical shift:
    - Calculate `y_shift = abs(min(Y))`
    - Compute baseline on `Y + y_shift`
    - Return corrected data as `(Y - baseline)` in original scale

**UI Changes**

- Add tooltip near baseline controls: "Negative Y values are automatically handled via internal shifting"[^1]
- When shift is applied, show brief status message: "Applied automatic Y-shift for baseline stability"[^1]
- No user intervention required; process is transparent and automatic

**Documentation**

- Log shift amount in project state JSON for transparency[^1]
- Help text explains that constant shifts do not affect baseline-corrected results

***

### FR-14: Adjustable Plot Width

**Priority:** Medium
**Rationale:** Current fixed-width plots are too wide for detailed spectrum inspection on some displays.[^1]

**Implementation**

- Add **Plot Width** control in sidebar or above main plot area
- Four preset options:
    - **Compact** (60% content width)
    - **Standard** (75% content width) — default
    - **Wide** (90% content width)
    - **Full** (100% content width)

**Behavior**

- Setting applies globally to all plots across tabs (Pre-process, Fit Model, Visualize \& Export)[^1]
- Plotly interactivity (zoom, pan, hover) preserved at all widths[^1]
- Choice persisted in session state and project JSON[^1]
- Session-level setting (same for all files in current session)[^1]

***

### FR-15: X-Range Selection for Focused Processing

**Priority:** High
**Rationale:** Enables precise analysis of specific spectral regions without interference from noisy edges or irrelevant features.[^1]

**UI Controls (Tab 1: Pre-process)**
Add new section **"Processing Range"** above de-spiking controls:

- Checkbox: `Limit to X range` (default: unchecked)[^1]
- Numeric inputs: `X min`, `X max` (units auto-set by mode: cm⁻¹ or nm)[^1]
- Auto-populated with full data range on file load

**Processing Behavior**

**When unchecked:**

- All operations use full spectrum (v2.0 behavior)[^1]

**When checked:**

- **Spike removal:**
    - Detect spikes on **full spectrum** (consistent diagnostics)[^1]
    - Replace spikes **only within** `[X min, X max]`[^1]
    - Outside range: spikes detected but not modified
- **Baseline correction:**
    - Compute baseline using **only** data within `[X min, X max]`[^1]
    - Correct Y values only in focus range
    - Outside range: data remains unprocessed and greyed-out in plots[^1]
- **Fitting (Tab 2):**
    - Add checkbox: `Fit only within X range` (default: ON)[^1]
    - When ON: fitting uses only `[X min, X max]` data points[^1]
    - When OFF: fitting uses full spectrum including unprocessed regions

**Visual Indicators**

- Vertical dashed lines or shaded regions mark `X min` and `X max` boundaries[^1]
- Data outside processing range displayed at 30% opacity[^1]
- Active range clearly visible in all plot views

**State \& Export**

- X range settings saved **per-file** in project JSON[^1]
- Master CSV export includes columns: `x_range_limited` (TRUE/FALSE), `x_min`, `x_max`[^1]

***

## Updated Export Schema

**Master CSV — New Columns**

```
filename, mode, auto_detected, x_range_limited, x_min, x_max, 
peak_label, center, amplitude, FWHM, shape, chi2, R2
```



## Backward Compatibility

- **v2.0 project files:** Fully compatible; missing fields auto-populated with defaults[^1]
    - `x_range.enabled = false`
    - `plot_width_preset = "Standard"`
    - `auto_detected = false`
- **Export CSV:** New columns appended; existing analysis tools unaffected[^1]

***

**Approval:** Ready for implementation
**Next Step:** Developer review and sprint planning for 4-week delivery cycle


