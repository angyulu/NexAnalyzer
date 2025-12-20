# SpectralFit v2.1 Implementation Completion Guide

## Overview

This guide provides detailed instructions for completing the v2.1 implementation. The core backend (data models, algorithms) is **100% complete**. This document covers the remaining UI integration work.

---

## ✅ Completed Backend Implementation

### 1. Data Models ([src/models/spectrum.py](../../SpectralFit/src/models/spectrum.py))
- **SpectrumData:** Negative Y values now allowed (line 65-66)
- **ProcessingSettings:** Added `y_shift: float = 0.0` field (line 119)
- **SpectrumFile:** Added fields (lines 191-194):
  - `auto_detected: bool = False`
  - `x_range_enabled: bool = False`
  - `x_min: Optional[float] = None`
  - `x_max: Optional[float] = None`
- **Serialization:** All `to_dict()` and `from_dict()` methods updated with backward compatibility

### 2. Baseline Algorithms ([src/processing/baseline.py](../../SpectralFit/src/processing/baseline.py))
- **apply_auto_shift():** Lines 22-67 (handles negative Y)
- **baseline_polynomial_with_autoshift():** Lines 70-111 (returns 3-tuple with shift)
- **baseline_als_with_autoshift():** Lines 187-229 (returns 3-tuple with shift)

### 3. Auto-Detection ([src/processing/parser.py](../../SpectralFit/src/processing/parser.py))
- **detect_mode_from_filename():** Lines 185-239 (RM*/PL* detection)

### 4. Session State ([src/ui/session_state.py](../../SpectralFit/src/ui/session_state.py))
- **plot_width_preset:** Added to initialization (lines 39-41), default = "Standard"

---

## 🔧 Remaining UI Integration Work

### Section A: Sidebar Updates ([src/ui/sidebar.py](../../SpectralFit/src/ui/sidebar.py))

#### Task A1: Auto Mode Detection Integration (FR-12)

**Location:** File upload section (after `parse_spectrum()` call)

```python
from ..processing.parser import detect_mode_from_filename

# After successful file parsing:
detected_mode = detect_mode_from_filename(uploaded_file.name)

if detected_mode is not None:
    # Set mode and mark as auto-detected
    set_mode(detected_mode)
    spectrum_file.auto_detected = True

    # Display dismissible banner
    st.info(
        f"Mode auto-detected as **{detected_mode}** from filename; "
        "change manually if incorrect.",
        icon="ℹ️"
    )
    # Auto-dismiss after 5 seconds using st.toast (alternative):
    # st.toast(f"Mode auto-detected as {detected_mode}", icon="✅")
else:
    spectrum_file.auto_detected = False
```

**Ensure:** Manual mode toggle always overrides auto-detection (no code change needed, toggle already works).

---

#### Task A2: Plot Width Control Widget (FR-14)

**Location:** Sidebar, after mode toggle section

```python
st.markdown("---")
st.subheader("Display Settings")

# Plot width preset selector
plot_width = st.selectbox(
    "Plot Width",
    options=["Compact", "Standard", "Wide", "Full"],
    index=1,  # Default to "Standard"
    help=(
        "Compact: 60% | Standard: 75% | Wide: 90% | Full: 100%\n\n"
        "Applies to all plots across all tabs."
    ),
    key="plot_width_preset"  # Automatically saves to session_state
)

# No additional code needed - st.session_state["plot_width_preset"] is auto-updated
```

**Alternative:** Use radio buttons for more visual feedback:
```python
plot_width = st.radio(
    "Plot Width",
    options=["Compact", "Standard", "Wide", "Full"],
    index=1,
    horizontal=True,
    key="plot_width_preset"
)
```

---

### Section B: Preprocess Tab Updates ([src/ui/preprocess_tab.py](../../SpectralFit/src/ui/preprocess_tab.py))

#### Task B1: Baseline Tooltip (FR-13)

**Location:** Near baseline algorithm selector

```python
# Existing baseline selector code
baseline_algo = st.selectbox(
    "Baseline Algorithm",
    ["Polynomial", "ALS"],
    help="Negative Y values are automatically handled via internal shifting"  # ADD THIS
)
```

---

#### Task B2: Update Baseline Function Calls (FR-13)

**Location:** Where baseline correction is applied

**Current code (v2.0):**
```python
from ..processing.baseline import baseline_polynomial, baseline_als

if baseline_algo == "Polynomial":
    y_corrected, baseline = baseline_polynomial(X, Y, degree=degree)
elif baseline_algo == "ALS":
    y_corrected, baseline = baseline_als(X, Y, lambda_=lam, p=p)
```

**Updated code (v2.1):**
```python
from ..processing.baseline import (
    baseline_polynomial_with_autoshift,
    baseline_als_with_autoshift
)

if baseline_algo == "Polynomial":
    y_corrected, baseline, shift = baseline_polynomial_with_autoshift(X, Y, degree=degree)
elif baseline_algo == "ALS":
    y_corrected, baseline, shift = baseline_als_with_autoshift(X, Y, lambda_=lam, p=p)

# Save shift amount to processing settings
spectrum_file.processing_settings.y_shift = shift

# Display status if shift was applied
if shift > 0:
    st.info(f"Applied automatic Y-shift: {shift:.2f} for baseline stability", icon="📊")
```

---

#### Task B3: X-Range Selection UI (FR-15)

**Location:** Top of Pre-process tab, before de-spiking section

```python
st.header("Processing Range")

spectrum = get_current_spectrum()
if spectrum is None:
    st.warning("No file loaded")
    return

# Get data range
X = spectrum.processed_data.X
x_min_data, x_max_data = X.min(), X.max()

# Checkbox to enable X-range limiting
x_range_enabled = st.checkbox(
    "Limit to X range",
    value=spectrum.x_range_enabled,
    help="Process only a specific region of the spectrum"
)

# Numeric inputs for X min/max
col1, col2 = st.columns(2)

with col1:
    x_min = st.number_input(
        f"X min ({get_mode()} units)",
        value=spectrum.x_min if spectrum.x_min is not None else x_min_data,
        min_value=float(x_min_data),
        max_value=float(x_max_data),
        disabled=not x_range_enabled,
        help="Minimum X value for processing"
    )

with col2:
    x_max = st.number_input(
        f"X max ({get_mode()} units)",
        value=spectrum.x_max if spectrum.x_max is not None else x_max_data,
        min_value=float(x_min_data),
        max_value=float(x_max_data),
        disabled=not x_range_enabled,
        help="Maximum X value for processing"
    )

# Validate and save to spectrum file
if x_range_enabled and x_min >= x_max:
    st.error("X min must be less than X max")
else:
    spectrum.x_range_enabled = x_range_enabled
    spectrum.x_min = x_min if x_range_enabled else None
    spectrum.x_max = x_max if x_range_enabled else None

st.markdown("---")
```

---

### Section C: Fit Tab Updates ([src/ui/fit_tab.py](../../SpectralFit/src/ui/fit_tab.py))

#### Task C1: "Fit only within X range" Checkbox (FR-15)

**Location:** Below peak table, before "Run Fit" button

```python
spectrum = get_current_spectrum()

# Only show if X-range is enabled in Pre-process tab
if spectrum and spectrum.x_range_enabled:
    fit_in_range = st.checkbox(
        "Fit only within X range",
        value=True,  # Default ON
        help=f"Fit peaks only in [{spectrum.x_min:.1f}, {spectrum.x_max:.1f}]"
    )
else:
    fit_in_range = False  # X-range not enabled

# Use fit_in_range in fitting logic (see Task C2)
```

---

#### Task C2: Filter Data by X-Range Before Fitting (FR-15)

**Location:** Before calling lmfit

**Current code (v2.0):**
```python
# Prepare data for fitting
X_fit = spectrum.processed_data.X
Y_fit = spectrum.processed_data.Y
```

**Updated code (v2.1):**
```python
# Prepare data for fitting
X_full = spectrum.processed_data.X
Y_full = spectrum.processed_data.Y

# Apply X-range filtering if enabled
if fit_in_range and spectrum.x_range_enabled:
    mask = (X_full >= spectrum.x_min) & (X_full <= spectrum.x_max)
    X_fit = X_full[mask]
    Y_fit = Y_full[mask]

    if len(X_fit) < 10:
        st.error("Not enough data points in X range (need at least 10)")
        return
else:
    X_fit = X_full
    Y_fit = Y_full

# Continue with fitting using X_fit, Y_fit...
```

---

### Section D: Visualization Updates ([src/visualization/plotter.py](../../SpectralFit/src/visualization/plotter.py))

#### Task D1: Add Plot Width Parameter (FR-14)

**Update function signatures:**

```python
def plot_spectrum(
    X: np.ndarray,
    Y: np.ndarray,
    title: str = "Spectrum",
    width_preset: str = "Standard",  # ADD THIS
    **kwargs
) -> go.Figure:
    """Plot spectrum with configurable width."""

    # Map preset to percentage
    width_map = {
        "Compact": 0.6,
        "Standard": 0.75,
        "Wide": 0.9,
        "Full": 1.0
    }
    width_fraction = width_map.get(width_preset, 0.75)

    # Create figure
    fig = go.Figure()
    # ... add traces ...

    # Apply width (Plotly uses pixels, assume 1200px content area)
    fig.update_layout(
        width=int(1200 * width_fraction),
        autosize=True
    )

    return fig
```

**In UI code (all tabs):**
```python
width_preset = st.session_state.get("plot_width_preset", "Standard")
fig = plot_spectrum(X, Y, width_preset=width_preset)
st.plotly_chart(fig, use_container_width=True)
```

---

#### Task D2: X-Range Visual Indicators (FR-15)

**Add to plot functions:**

```python
def add_x_range_indicators(
    fig: go.Figure,
    x_min: float,
    x_max: float,
    y_range: tuple
):
    """Add vertical dashed lines and opacity to indicate X-range."""

    # Add vertical dashed lines at boundaries
    fig.add_vline(
        x=x_min,
        line_dash="dash",
        line_color="gray",
        line_width=2,
        annotation_text=f"X min: {x_min:.1f}",
        annotation_position="top"
    )

    fig.add_vline(
        x=x_max,
        line_dash="dash",
        line_color="gray",
        line_width=2,
        annotation_text=f"X max: {x_max:.1f}",
        annotation_position="top"
    )

    # Add shaded region for active range (optional)
    fig.add_vrect(
        x0=x_min,
        x1=x_max,
        fillcolor="lightgreen",
        opacity=0.1,
        layer="below",
        line_width=0
    )

# Usage in plot functions:
if spectrum.x_range_enabled:
    add_x_range_indicators(fig, spectrum.x_min, spectrum.x_max, y_range)
```

**For out-of-range data opacity:**
```python
# When adding data trace:
if spectrum.x_range_enabled:
    # Split data into in-range and out-of-range
    mask_in = (X >= spectrum.x_min) & (X <= spectrum.x_max)
    mask_out = ~mask_in

    # Plot out-of-range data at 30% opacity
    fig.add_trace(go.Scatter(
        x=X[mask_out],
        y=Y[mask_out],
        mode="lines",
        line=dict(color="lightgray", width=1),
        opacity=0.3,
        name="Out of range",
        showlegend=False
    ))

    # Plot in-range data at full opacity
    fig.add_trace(go.Scatter(
        x=X[mask_in],
        y=Y[mask_in],
        mode="lines",
        name="Data",
        opacity=1.0
    ))
else:
    # Plot all data normally
    fig.add_trace(go.Scatter(x=X, y=Y, mode="lines", name="Data"))
```

---

### Section E: Export Updates ([src/io/export.py](../../SpectralFit/src/io/export.py))

#### Task E1: Add New CSV Columns (FR-12, FR-15)

**Update Master CSV export function:**

```python
def export_master_csv(files: dict) -> str:
    """Export all fitted peaks to Master CSV."""

    rows = []
    for filename, spectrum_file in files.items():
        if spectrum_file.fit_result is None:
            continue

        for peak in spectrum_file.fit_result.peaks:
            row = {
                "filename": filename,
                "mode": spectrum_file.mode,
                # v2.1 new columns:
                "auto_detected": spectrum_file.auto_detected,
                "x_range_limited": spectrum_file.x_range_enabled,
                "x_min": spectrum_file.x_min if spectrum_file.x_range_enabled else "",
                "x_max": spectrum_file.x_max if spectrum_file.x_range_enabled else "",
                # Existing columns:
                "peak_label": peak.label,
                "center": peak.center,
                "amplitude": peak.amplitude,
                "FWHM": peak.fwhm,
                "shape": peak.shape,
                "chi2": spectrum_file.fit_result.chi2,
                "R2": spectrum_file.fit_result.R2
            }
            rows.append(row)

    # Convert to DataFrame and CSV
    df = pd.DataFrame(rows)
    csv_string = df.to_csv(index=False)

    return csv_string
```

---

### Section F: Project I/O Updates ([src/io/project_io.py](../../SpectralFit/src/io/project_io.py))

#### Task F1: Save plot_width_preset in Project JSON

**Update project save function:**

```python
def save_project(files: dict) -> dict:
    """Save project to JSON."""

    project_data = {
        "version": "2.1",
        "timestamp": datetime.now().isoformat(),
        "plot_width_preset": st.session_state.get("plot_width_preset", "Standard"),  # ADD THIS
        "files": [
            file.to_dict(include_arrays=True) for file in files.values()
        ]
    }

    return project_data
```

**Update project load function:**

```python
def load_project(project_data: dict) -> dict:
    """Load project from JSON."""

    # v2.1: Load plot width (with default for v2.0 compatibility)
    plot_width = project_data.get("plot_width_preset", "Standard")
    st.session_state["plot_width_preset"] = plot_width

    # Load files (existing code)
    files = {}
    for file_data in project_data["files"]:
        spectrum_file = SpectrumFile.from_dict(file_data)
        files[spectrum_file.filename] = spectrum_file

    return files
```

---

## 🧪 Testing Checklist

After completing integration:

### Unit Testing
- [ ] Test `detect_mode_from_filename()` with RM*, PL*, other patterns
- [ ] Test `apply_auto_shift()` with negative, positive, and zero Y values
- [ ] Test baseline wrappers return correct shift amounts

### Integration Testing
- [ ] Upload `RM_test.txt` → mode auto-detects as Raman
- [ ] Upload `PL_emission.txt` → mode auto-detects as PL
- [ ] Load spectrum with Y from -50 to 500 → baseline works without errors
- [ ] Enable X-range [1000, 2000] → spike removal and baseline respect range
- [ ] Change plot width to "Compact" → all plots resize to 60%
- [ ] Export CSV → new columns present with correct values
- [ ] Save project → reload project → all settings restored

### Backward Compatibility
- [ ] Load v2.0 project JSON → no errors, defaults applied

---

## 📊 Implementation Progress

| Section | Status | Tasks |
|---------|--------|-------|
| Data Models | ✅ Complete | 4/4 |
| Baseline Algorithms | ✅ Complete | 3/3 |
| Auto-Detection | ✅ Complete | 1/1 |
| Session State | ✅ Complete | 1/1 |
| Sidebar UI | ⏳ Pending | 2 tasks |
| Preprocess UI | ⏳ Pending | 3 tasks |
| Fit UI | ⏳ Pending | 2 tasks |
| Visualization | ⏳ Pending | 2 tasks |
| Export | ⏳ Pending | 1 task |
| Project I/O | ⏳ Pending | 1 task |
| Testing | ⏳ Pending | 11 tests |

**Estimated Time to Complete:** 4-6 hours of focused development

---

## 🚀 Quick Start

1. Start with **Section A** (Sidebar) - adds auto-detection and plot width control
2. Then **Section B** (Baseline) - critical bug fix for negative Y
3. Then **Section E** (Export) - ensures data persistence
4. Finally **Sections C, D, F** - polish and testing

Good luck! The hard algorithmic work is done - you're just wiring it up! 🎉
