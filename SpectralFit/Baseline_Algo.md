# Baseline Correction Algorithm Analysis

**Date:** 2025-12-21
**Version:** SpectralFit v2.2+
**Status:** Analysis Complete

---

## Table of Contents

1. [Overview](#1-overview)
2. [Fundamental Theory](#2-fundamental-theory)
3. [Current Implementation](#3-current-implementation)
4. [Identified Issues](#4-identified-issues)
5. [Root Cause Analysis](#5-root-cause-analysis)
6. [Proposed Solutions](#6-proposed-solutions)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Overview

### Purpose
Baseline correction removes broad background signals (fluorescence, detector offset, sample fluorescence) from Raman/PL spectra to isolate true spectral peaks.

### User-Reported Issues
1. **"Hard to tune the parameter"** - Parameters are not intuitive
2. **"Baseline fit poorly"** - Quality issues with current algorithms
3. **"Usually overfit and fit into the peak part"** - Baseline goes through peaks instead of under them

### Current Algorithms
- **Polynomial Baseline** (default): Fits polynomial curve to data
- **ALS (Asymmetric Least Squares)**: Iteratively fits smooth curve favoring points below current estimate

---

## 2. Fundamental Theory

### 2.1 The Baseline Problem

**Physical Origin:**
- **Fluorescence background**: Broad emission from sample/substrate
- **Detector offset**: Constant or slowly varying instrument baseline
- **Sample scattering**: Rayleigh/Raman background

**Mathematical Definition:**
Given measured spectrum `Y(x)`:
```
Y(x) = Signal(x) + Baseline(x) + Noise(x)
```

**Goal:** Estimate `Baseline(x)` to obtain `Signal(x) = Y(x) - Baseline(x)`

**Key Challenges:**
1. Baseline and signal overlap in frequency space (both can be smooth or sharp)
2. Peaks sit **above** baseline, but baseline fitting sees them as "data to fit"
3. No universal "correct" baseline (subjective, application-dependent)

---

### 2.2 Polynomial Baseline Theory

**Mathematical Formulation:**

Fit polynomial of degree `n`:
```
Baseline(x) = a₀ + a₁x + a₂x² + ... + aₙxⁿ
```

Find coefficients `{a₀, a₁, ..., aₙ}` that minimize:
```
SSE = Σ [Y(xᵢ) - Baseline(xᵢ)]²
```

**Implementation:**
- Uses **orthogonal polynomials** (Legendre/Chebyshev) via `numpy.polynomial.Polynomial.fit()`
- Numerically stable for high degrees (avoids Vandermonde matrix conditioning issues)
- Least-squares fitting across **all data points**

**Strengths:**
- ✅ Fast computation (closed-form solution)
- ✅ Deterministic (same input → same output)
- ✅ Simple to understand (degree controls flexibility)
- ✅ Good for smooth, monotonic fluorescence backgrounds

**Weaknesses:**
- ❌ **Overfitting**: High-degree polynomials oscillate through peaks (Runge's phenomenon)
- ❌ **Symmetric treatment**: Peaks get same weight as baseline regions
- ❌ **No peak awareness**: Minimizes global error, doesn't know peaks should be excluded
- ❌ **Oscillation risk**: Degree >6 can produce unphysical wiggles

**When to Use:**
- Simple fluorescence backgrounds (broad, monotonic)
- Degree 1-3 for most cases
- When speed is critical

---

### 2.3 ALS (Asymmetric Least Squares) Theory

**Reference:** Eilers & Boelens (2005), "Baseline Correction with Asymmetric Least Squares Smoothing"

**Mathematical Formulation:**

Find baseline `z(x)` that minimizes:
```
Cost = Σ wᵢ[yᵢ - zᵢ]² + λ Σ [Δ²zᵢ]²
       ↑                    ↑
   Fidelity term      Smoothness penalty
```

Where:
- `wᵢ` = asymmetric weights (key innovation!)
- `λ` = smoothness parameter (controls 2nd derivative penalty)
- `Δ²zᵢ` = discrete 2nd derivative (penalizes curvature)

**Asymmetric Weighting (KEY CONCEPT):**
```
       ⎧ p       if yᵢ > zᵢ  (point above baseline)
wᵢ =   ⎨
       ⎩ 1-p     if yᵢ ≤ zᵢ  (point below baseline)
```

At `p = 0.001` (default):
- Points **above** baseline: `w = 0.001` (almost ignore)
- Points **below** baseline: `w = 0.999` (almost full weight)
- **Ratio:** 1:999 (highly asymmetric)

**Intuition:**
- Baseline should pass **below** peaks, not through them
- Give low weight to points above current baseline estimate (likely peaks)
- Give high weight to points below (likely true baseline)
- Iterate until convergence

**Algorithm (Iterative):**
```python
# Initialize
w = np.ones(n)  # Equal weights initially
D = 2nd_derivative_operator  # Sparse (n-2)×n matrix

for iteration in range(max_iter):
    # Solve weighted least-squares with smoothness penalty
    # (W + λD^T D) z = W y
    baseline = sparse_solve(W + lambda*D^T*D, W*y)

    # Update asymmetric weights
    w_new = p * (y > baseline) + (1-p) * (y <= baseline)

    # Check convergence
    if ||w - w_new|| < tolerance:
        break
    w = w_new
```

**Parameters:**

1. **Lambda (λ)**: Smoothness parameter
   - **Range:** 10³ to 10⁶ (1000× span, logarithmic scale)
   - **Low λ (e.g., 10³):** Very flexible baseline, follows data closely (risk: follows noise)
   - **High λ (e.g., 10⁶):** Very smooth baseline, ignores fine structure (risk: too flat)
   - **Typical:** 10⁴ to 10⁵ for Raman/PL fluorescence
   - **Physical meaning:** "How much curvature penalty to apply?"

2. **Asymmetry (p)**: Weight for points above baseline
   - **Range:** 0.001 to 0.1
   - **Low p (e.g., 0.001):** Highly asymmetric, strongly favors points below (risk: over-penalizes peaks)
   - **High p (e.g., 0.1):** Less asymmetric, more symmetric weighting (risk: fits through peaks)
   - **Typical:** 0.001-0.01 for peak-heavy spectra
   - **Physical meaning:** "How much should I ignore points above the baseline?"

**Strengths:**
- ✅ **Peak-aware**: Asymmetric weighting naturally avoids peaks
- ✅ **Smooth control**: λ directly controls baseline roughness
- ✅ **No degree selection**: Single parameter (λ) controls flexibility
- ✅ **Excellent for fluorescence**: Designed for spectroscopy applications

**Weaknesses:**
- ❌ **Two parameters**: λ and p must both be tuned (interaction effects)
- ❌ **Non-intuitive**: λ scale is logarithmic, p semantics are technical
- ❌ **Iterative**: Slower than polynomial (requires matrix solves)
- ❌ **Over-suppression risk**: Very low p (e.g., 0.001) can pull baseline too far below peaks

**When to Use:**
- Complex fluorescence backgrounds with sharp peaks
- When peaks must be strictly avoided
- High signal-to-noise spectra

---

## 3. Current Implementation

### 3.1 Code Structure

**File:** `src/processing/baseline.py` (393 lines)

**Functions:**
1. `baseline_polynomial(x, y, degree)` - Core polynomial fitting
2. `baseline_als(x, y, lambda_, p, max_iter)` - Core ALS fitting
3. `baseline_polynomial_with_autoshift(x, y, degree)` - Polynomial wrapper with auto Y-shift
4. `baseline_als_with_autoshift(x, y, lambda_, p, max_iter)` - ALS wrapper with auto Y-shift
5. `apply_auto_shift(y, epsilon)` - Handle negative Y values
6. `estimate_baseline_degree(x, y)` - Suggest polynomial degree (heuristic)

---

### 3.2 Polynomial Implementation

**Code (lines 114-184):**
```python
def baseline_polynomial(x, y, degree=3):
    """Fit and subtract polynomial baseline from spectrum."""

    # Validation
    if not (1 <= degree <= 10):
        raise ValueError(f"degree must be in [1, 10] (got {degree})")

    # Fit polynomial (orthogonal basis for numerical stability)
    p = Polynomial.fit(x, y, degree)

    # Evaluate baseline
    baseline = p(x)

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline
```

**Parameters:**
| Parameter | Range | Default | Current UI |
|-----------|-------|---------|------------|
| `degree` | 1-10 | 3 | Slider: 1-10, step=1 |

**Validation:**
- ✅ Degree bounds checked
- ✅ Requires `len(x) >= degree + 1`
- ✅ Checks `len(x) == len(y)`

**Issues:**
- No warning when degree >6 (high oscillation risk)
- No automatic peak masking (users must manually exclude peaks)

---

### 3.3 ALS Implementation

**Code (lines 232-346):**
```python
def baseline_als(x, y, lambda_=10000.0, p=0.001, max_iter=10):
    """Asymmetric Least Squares baseline correction."""

    # Validation
    if not (1000.0 <= lambda_ <= 1000000.0):
        raise ValueError(f"lambda_ must be in [1e3, 1e6] (got {lambda_})")

    if not (0.001 <= p <= 0.1):
        raise ValueError(f"p must be in [0.001, 0.1] (got {p})")

    n = len(y)

    # Build 2nd derivative operator (sparse matrix)
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(n-2, n))
    D_T_D = D.T @ D

    # Initialize weights (all equal initially)
    w = np.ones(n)

    # Iterative fitting
    for _ in range(max_iter):
        # Build weighted matrix: W + λD^T*D
        W = sparse.diags(w, 0, shape=(n, n))
        A = W + lambda_ * D_T_D

        # Solve: (W + λD^T*D) z = W y
        baseline = spsolve(A, w * y)

        # Update weights (asymmetric)
        w_new = p * (y > baseline) + (1 - p) * (y <= baseline)

        # Check convergence
        if np.allclose(w, w_new, rtol=1e-4):
            break

        w = w_new

    # Subtract baseline
    y_corrected = y - baseline

    return y_corrected, baseline
```

**Parameters:**
| Parameter | Range | Default | Current UI |
|-----------|-------|---------|------------|
| `lambda_` | 10³ - 10⁶ | 10⁴ | Slider: 10⁴ - 10⁷ ⚠️ BUG |
| `p` | 0.001 - 0.1 | 0.001 | Slider: 0.0001 - 0.01 |
| `max_iter` | ≥ 1 | 10 | Fixed (not exposed in UI) |

**Validation:**
- ✅ Lambda range checked
- ✅ Asymmetry range checked
- ✅ Convergence check (early termination if weights stabilize)
- ❌ **BUG:** UI slider max (10⁷) exceeds validation max (10⁶)

**Issues:**
- **UI/validation mismatch:** Users can set λ=10⁷ in UI, but it will error on "Run Baseline Correction"
- **Convergence monitoring:** No warning if max_iter reached without convergence
- **Default p=0.001:** Very aggressive asymmetry may over-suppress peaks in some cases

---

### 3.4 Auto-Shift for Negative Values

**Problem:** Many baseline algorithms assume non-negative intensities. After prior processing (despike, cropping), Y values may be negative.

**Solution (lines 22-67):**
```python
def apply_auto_shift(y, epsilon=1.0):
    """Apply automatic vertical shift to ensure non-negative Y values."""
    y_min = np.min(y)

    if y_min >= 0:
        return y, 0.0  # No shift needed
    else:
        shift = abs(y_min) + epsilon  # e.g., abs(-50) + 1 = 51
        return y + shift, shift
```

**Wrapper Functions:**
- `baseline_polynomial_with_autoshift()` (lines 70-111)
- `baseline_als_with_autoshift()` (lines 187-229)

**Workflow:**
1. Detect `min(Y) < 0`
2. Apply shift: `Y_shifted = Y + shift` (now all positive)
3. Run baseline algorithm on `Y_shifted`
4. Return baseline in **original scale**: `baseline_original = baseline_shifted - shift`
5. Return corrected data: `Y_corrected = Y - baseline_original`

**Key Points:**
- ✅ Transparent to user (shift logged but internal)
- ✅ Results always in original Y scale
- ✅ Epsilon=1.0 buffer ensures strict positivity
- ✅ No impact on final baseline shape (shift cancels out)

---

### 3.5 UI Integration

**File:** `src/ui/control_panel.py` (lines 340-479)

**Algorithm Selection:**
```python
baseline_alg = st.radio(
    "Algorithm",
    ["Polynomial", "ALS"],
    index=0 if spectrum.processing_settings.baseline_algorithm == "Polynomial" else 1,
    help="Polynomial: Simple fitting\nALS: Asymmetric Least Squares (better for fluorescence)"
)
```

**Polynomial Parameters:**
```python
degree = st.slider(
    "Polynomial Degree",
    min_value=1,
    max_value=10,
    value=spectrum.processing_settings.baseline_degree,
    help="Higher = more flexible (may overfit)"
)
```

**ALS Parameters:**
```python
lambda_val = st.slider(
    "Smoothness (λ)",
    min_value=10000.0,
    max_value=10000000.0,  # ⚠️ BUG: Exceeds validation max of 1e6
    value=max(spectrum.processing_settings.baseline_lambda, 100000.0),
    step=10000.0,
    format="%.0f",
    help="Higher = smoother baseline (typical: 100k-1M for fluorescence)"
)

p_val = st.slider(
    "Asymmetry (p)",
    min_value=0.0001,
    max_value=0.01,
    value=min(spectrum.processing_settings.baseline_p, 0.001),
    step=0.0001,
    format="%.4f",
    help="Lower = more asymmetric (weights below baseline more)"
)
```

**Real-Time Preview (lines 359-426):**
```python
show_preview = st.checkbox("Show Preview", value=False, ...)

if show_preview:
    # Non-destructive preview
    if baseline_alg == "Polynomial":
        y_corrected_preview, baseline_preview, y_shift = \
            baseline_polynomial_with_autoshift(X, Y, degree=degree)
    else:
        y_corrected_preview, baseline_preview, y_shift = \
            baseline_als_with_autoshift(X, Y, lambda_=lambda_val, p=p_val)

    # Store in session state for visualization
    st.session_state['baseline_preview'] = {
        'x': X,
        'baseline': baseline_preview,
        'corrected': y_corrected_preview
    }
```

**Apply Baseline (lines 427-470):**
```python
if st.button("Apply Baseline Correction", ...):
    if baseline_alg == "Polynomial":
        y_corrected, baseline, y_shift = baseline_polynomial_with_autoshift(X, Y, degree)
    else:
        y_corrected, baseline, y_shift = baseline_als_with_autoshift(X, Y, lambda_val, p_val)

    # Update spectrum state
    spectrum.processed_data = SpectrumData(X=X, Y=y_corrected)
    spectrum.baseline_done = True
```

---

### 3.6 Default Values

**From `src/models/spectrum.py` (ProcessingSettings dataclass):**
```python
despike_threshold: float = 6.0
baseline_algorithm: Literal["Polynomial", "ALS"] = "Polynomial"
baseline_degree: int = 3
baseline_lambda: float = 10000.0
baseline_p: float = 0.001
```

**Summary:**
- Default algorithm: **Polynomial**
- Default degree: **3** (cubic)
- Default λ: **10⁴** (1e4)
- Default p: **0.001** (highly asymmetric)

---

## 4. Identified Issues

Based on user feedback and code analysis, here are the critical problems:

---

### Issue 1: Parameter Intuitiveness ⚠️

**User Complaint:** "Hard to tune the parameter"

**Root Causes:**

#### A. Lambda (λ) Scale is Logarithmic, but UI is Linear
```python
# Current UI slider
lambda_val = st.slider(
    "Smoothness (λ)",
    min_value=10000.0,      # 1e4
    max_value=10000000.0,   # 1e7
    step=10000.0            # Linear steps of 10k
)
```

**Problem:**
- Parameter range: 10⁴ to 10⁷ (1000× span)
- Slider steps: Linear increments of 10k
- **Result:** Most of slider range is "dead space" at low end, tiny movements at high end cause huge changes

**Example:**
- Moving slider from 10k → 20k: 2× change (noticeable effect)
- Moving slider from 1M → 1.01M: 1% change (imperceptible)
- **User perception:** "Random behavior, can't control it"

**Expected behavior:** Logarithmic scale (1e3, 1e4, 1e5, 1e6) with exponential slider

#### B. Asymmetry (p) Semantics are Confusing
```python
p_val = st.slider(
    "Asymmetry (p)",
    min_value=0.0001,
    max_value=0.01,
    help="Lower = more asymmetric (weights below baseline more)"
)
```

**Problem:**
- Help text is technically correct but unintuitive
- "Asymmetry = 0.001" sounds like "1% asymmetric"
- **Reality:** p=0.001 means 999:1 weight ratio (above:below)
- Users don't understand "lower p = stronger peak avoidance"

**Example:**
- User wants to "avoid peaks more" → Should decrease p
- User sees p=0.001, thinks "already at 0.1%, can't go lower"
- **Confusion:** "Why is baseline still fitting through peaks?"

#### C. Polynomial Degree is Intuitive but Lacks Guidance
```python
degree = st.slider(
    "Polynomial Degree",
    min_value=1,
    max_value=10,
    help="Higher = more flexible (may overfit)"
)
```

**Problem:**
- "May overfit" is vague warning
- No guidance on when degree >6 is dangerous
- No auto-suggestion based on data characteristics (despite `estimate_baseline_degree()` existing in code!)

---

### Issue 2: Baseline Overfitting into Peaks ⚠️⚠️⚠️

**User Complaint:** "Usually overfit and fit into the peak part"

**Root Causes:**

#### A. Polynomial Overfitting (Runge's Phenomenon)
High-degree polynomials oscillate through data points to minimize global squared error.

**Example Scenario:**
- Spectrum: Broad fluorescence + sharp Raman peak at 1580 cm⁻¹
- User sets: Degree = 6
- **Result:** Polynomial "fits" the peak as part of baseline curve

**Mathematical Reason:**
- Polynomial minimizes `Σ[Y - Baseline]²` globally
- Peak has high amplitude → large squared error if ignored
- High degree gives flexibility to "capture" peak shape
- **No asymmetry:** Peak points get same weight as baseline points

**Visualization:**
```
Y data:    ____/‾‾‾‾\____  (fluorescence + peak)
Degree 2:  ___/      \___  (smooth, under peak) ✓
Degree 6:  ___/‾‾‾‾\_____  (oscillates through peak) ✗
```

#### B. ALS Over-Suppression with Low p
At `p=0.001` (default), points above baseline get weight 0.001 (almost ignored).

**Example Scenario:**
- Spectrum: Multiple sharp peaks on broad background
- User sets: λ=1e5, p=0.001
- **Result:** Baseline pulls **too far below** peaks, corrected spectrum has artificially high peaks

**Mathematical Reason:**
```python
w = p * (y > baseline) + (1-p) * (y <= baseline)
# w[peak] = 0.001 (almost zero weight)
# w[background] = 0.999 (full weight)
```

- Peaks get 1/999 the weight of background
- Optimizer "ignores" peak regions entirely
- Baseline can drift into valleys between peaks
- **Result:** Baseline goes **through** peak shoulders

**Visualization:**
```
Y data:       ____/‾‾\____/‾‾\____
Baseline:     ___/___\___/___\___  (dips into valleys) ✗
Expected:     ____________________  (flat, below peaks) ✓
```

#### C. No Peak Masking / Exclusion
Neither algorithm allows users to **manually exclude peak regions** from baseline fitting.

**Industry Standard (absent in SpectralFit):**
- Bruker OPUS: "Exclude regions" feature
- LabSpec: Manual baseline anchor points
- OriginLab: "Mask peaks" before baseline fit

**Example Use Case:**
- User knows D-band is at 1350 cm⁻¹, G-band at 1580 cm⁻¹
- Wants to exclude 1300-1400, 1550-1620 from baseline fitting
- **Current SpectralFit:** Not possible, must fit over entire range

---

### Issue 3: Baseline Fitting Quality ⚠️

**User Complaint:** "Baseline fit poorly"

**Root Causes:**

#### A. Polynomial Lacks Local Flexibility
Polynomial is **global** - changes at one X position affect entire curve.

**Example:**
- Fluorescence background has small kink at 1000 cm⁻¹
- To fit kink, need degree ≥4
- But degree 4 also adds oscillations at 1500 cm⁻¹ (unwanted)
- **Result:** Can't fit local features without global artifacts

**Better Alternative:** Piecewise polynomials (splines) allow local control

#### B. ALS Smoothness is Uniform
λ penalty is applied uniformly across all X positions.

**Example:**
- Baseline has steep slope at low wavenumbers, flat at high wavenumbers
- λ=1e5 smooths steep region **and** flat region equally
- **Result:** Either over-smooths flat region or under-smooths steep region

**Better Alternative:** Adaptive smoothness based on local curvature

#### C. No Iterative Refinement / Outlier Rejection
Both algorithms run **once** on full data. No iterative peak detection + re-weighting.

**Industry Standard (absent):**
- **Iterative polynomial:** Fit → identify outliers (peaks) → mask → refit
- **Morphological baseline:** Rolling ball algorithm (local minima tracking)
- **Penalized splines:** Whittaker smoother with automatic roughness penalty

---

### Issue 4: UI/Validation Bugs 🐛

#### A. Lambda Slider Exceeds Validation Range
```python
# In control_panel.py (UI):
lambda_val = st.slider(..., max_value=10000000.0)  # 1e7

# In baseline.py (validation):
if not (1000.0 <= lambda_ <= 1000000.0):  # 1e6 max!
    raise ValueError(...)
```

**Impact:**
- User sets λ=5e6 via slider
- Clicks "Apply Baseline Correction"
- **Error:** `ValueError: lambda_ must be in [1e3, 1e6] (got 5000000.0)`
- User confusion: "Why did the UI let me set this value?"

#### B. No Warning for High Polynomial Degree
Code has no check for `degree > 6` despite oscillation risk.

**Impact:**
- User sets degree=10 (maximum allowed)
- Baseline shows extreme oscillations (Runge's phenomenon)
- No warning or guidance

#### C. estimate_baseline_degree() Not Used
Function exists (lines 349-392) but **never called** in UI or processing pipeline.

```python
def estimate_baseline_degree(x, y):
    """Suggest polynomial degree based on data characteristics."""
    # Heuristic logic implemented, but UNUSED
```

**Impact:**
- Missed opportunity for smart defaults
- Users must guess appropriate degree

---

### Issue 5: Missing Features from Industry Standards 📊

#### A. No Spline/Piecewise Baseline
- **Missing:** Cubic splines, B-splines, piecewise polynomials
- **Available:** Only global polynomials
- **Impact:** Can't fit complex baselines with local features

#### B. No Morphological Baseline (Rolling Ball)
- **Missing:** Rolling ball algorithm (local minima tracking)
- **Impact:** Poor performance on spectra with many sharp peaks

#### C. No Manual Baseline Points
- **Missing:** User-defined anchor points for baseline
- **Available:** Only automatic fitting
- **Impact:** Can't enforce baseline at specific Y values

#### D. No Peak Masking/Exclusion
- **Missing:** Ability to exclude regions from baseline fit
- **Impact:** Peaks always influence baseline (even with ALS asymmetry)

---

## 5. Root Cause Analysis

### 5.1 Why Polynomial Overfits

**Mathematical Explanation:**

Polynomial fitting minimizes global squared error:
```
SSE = Σᵢ [yᵢ - (a₀ + a₁xᵢ + a₂xᵢ² + ... + aₙxᵢⁿ)]²
```

**No distinction between:**
- Baseline regions (should fit closely)
- Peak regions (should be excluded)

**High degree = more free parameters:**
- Degree 2: 3 parameters (a₀, a₁, a₂)
- Degree 6: 7 parameters
- Degree 10: 11 parameters

**Runge's Phenomenon:**
When fitting high-degree polynomials to equally-spaced data with localized features (peaks), polynomial oscillates wildly between points to minimize global error.

**Example (degree 6 fitting spectrum with peak at center):**
```
True baseline:  ___________________  (flat)
Data Y:         _______/‾‾\_______  (flat + peak)
Polynomial fit: ____/‾‾‾‾‾\_______  (captures peak as baseline)
```

Why? Polynomial "sees" peak as "data to fit" and uses degree freedom to minimize error at peak location, creating oscillation.

---

### 5.2 Why ALS Overfits (Despite Asymmetry)

**Key Insight:** ALS asymmetry works **iteratively** based on **current baseline estimate**.

**Iteration 1:**
- Initial baseline: `z₀ = mean(y)` (or from polynomial guess)
- Points above z₀: weight = 0.001
- Points below z₀: weight = 0.999
- Fit new baseline z₁ favoring points below

**Iteration 2:**
- Update weights based on z₁
- **Problem:** If z₁ dips into valley between peaks, valley points now have `y > baseline` → weight 0.001
- Peak shoulders may have `y ≈ baseline` → weight transition
- **Result:** Baseline can "thread" through peak shoulders

**Root Cause:**
- p=0.001 is **too aggressive** for some spectra
- Creates binary weight distribution (almost 0 or 1)
- No gradient for smooth transition around peaks
- **Smoothness penalty (λ) fights asymmetry penalty (p)**

**Trade-off:**
- High λ + low p: Very smooth baseline, but may drift into peaks
- Low λ + low p: Follows valleys, "threads" through peaks
- **Goldilocks zone:** λ~1e5, p~0.005-0.01 (less explored by users)

---

### 5.3 Why Parameters are Hard to Tune

**Cognitive Load Issues:**

1. **Lambda (λ):** Logarithmic meaning on linear scale
   - User thinks: "I'll increase by 10k" (slider step)
   - Reality: Effect depends on current value (10k→20k is 2×, 1M→1.01M is 1%)

2. **Asymmetry (p):** Inverse relationship to user intent
   - User wants: "Avoid peaks more"
   - Must do: Decrease p (counterintuitive, lower number = more avoidance)

3. **Degree:** Direct relationship but no guidance
   - User wants: "Better fit"
   - Tries: Higher degree
   - Gets: Worse fit (overfitting)
   - **Feedback loop:** More parameters → worse result → confusion

**Lack of Visual Feedback:**
- Preview is available but not default (checkbox must be enabled)
- No real-time update as slider moves (must release slider)
- No overlay of "good" vs "bad" baseline examples

---

## 6. Proposed Solutions

### 6.1 SHORT-TERM FIXES (High Impact, Low Effort)

#### Solution 1: Fix Lambda Slider Range (CRITICAL BUG FIX)
**Priority:** 🔴 HIGH
**Effort:** 5 minutes
**Impact:** Prevents validation errors

**Change:**
```python
# In control_panel.py, change:
max_value=10000000.0,  # 1e7 (WRONG)
# To:
max_value=1000000.0,   # 1e6 (matches validation)
```

**Files:** `src/ui/control_panel.py` line ~380

---

#### Solution 2: Use Logarithmic Slider for Lambda
**Priority:** 🔴 HIGH
**Effort:** 15 minutes
**Impact:** Vastly improved parameter control

**Implementation:**
```python
# Replace linear slider with log-scale slider
import numpy as np

# Slider in log10 space
lambda_log = st.slider(
    "Smoothness (log₁₀ λ)",
    min_value=3.0,   # 10^3 = 1,000
    max_value=6.0,   # 10^6 = 1,000,000
    value=np.log10(spectrum.processing_settings.baseline_lambda),
    step=0.1,
    format="%.1f",
    help="Higher = smoother baseline. Log scale: 3=1k, 4=10k, 5=100k, 6=1M"
)

# Convert back to linear for algorithm
lambda_val = 10 ** lambda_log

# Display actual value
st.caption(f"Actual λ = {lambda_val:,.0f}")
```

**User Experience:**
- Slider range: 3.0 to 6.0 (log scale)
- Position 3.0 → λ=1,000
- Position 4.0 → λ=10,000
- Position 5.0 → λ=100,000
- Position 6.0 → λ=1,000,000
- **Uniform sensitivity** across entire range

**Alternative (Even Better):** Preset buttons + fine-tune slider
```python
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("Low (1e4)"):
        st.session_state['lambda_preset'] = 1e4
with col2:
    if st.button("Medium (1e5)"):
        st.session_state['lambda_preset'] = 1e5
with col3:
    if st.button("High (5e5)"):
        st.session_state['lambda_preset'] = 5e5
with col4:
    if st.button("Very High (1e6)"):
        st.session_state['lambda_preset'] = 1e6

# Fine-tune around preset
lambda_val = st.slider(
    "Fine-tune λ",
    min_value=0.5 * st.session_state.get('lambda_preset', 1e5),
    max_value=2.0 * st.session_state.get('lambda_preset', 1e5),
    value=st.session_state.get('lambda_preset', 1e5),
    step=st.session_state.get('lambda_preset', 1e5) * 0.05,
    format="%.0f"
)
```

**Files:** `src/ui/control_panel.py` lines ~375-390

---

#### Solution 3: Rephrase Asymmetry Parameter (p) for Clarity
**Priority:** 🟡 MEDIUM
**Effort:** 2 minutes
**Impact:** Better user understanding

**Change:**
```python
# Current (confusing):
p_val = st.slider(
    "Asymmetry (p)",
    help="Lower = more asymmetric (weights below baseline more)"
)

# Proposed (clearer):
p_val = st.slider(
    "Peak Avoidance",
    min_value=0.001,
    max_value=0.01,
    value=0.001,
    step=0.001,
    format="%.3f",
    help=(
        "Controls how strongly the baseline avoids peaks.\n"
        "• 0.001 (default): Very strong avoidance (ignores peaks completely)\n"
        "• 0.005: Moderate avoidance (typical for complex spectra)\n"
        "• 0.01: Gentle avoidance (risk of fitting through small peaks)"
    )
)

st.caption(f"Technical: p={p_val:.4f}, weight ratio (above:below) = 1:{int((1-p_val)/p_val)}")
```

**User Experience:**
- Parameter name: "Peak Avoidance" (direct intent)
- Help text: Explicit examples with consequences
- Caption: Shows technical details for advanced users (weight ratio)

**Alternative:** Invert scale to match user intuition
```python
# User sees: "Peak Sensitivity" from 0-100%
peak_sensitivity = st.slider(
    "Peak Sensitivity",
    min_value=0,
    max_value=100,
    value=10,  # Default: low sensitivity (avoids peaks)
    help="How sensitive baseline is to peaks. Low=avoids peaks, High=follows peaks"
)

# Convert to p (inverse relationship)
p_val = 0.001 + (peak_sensitivity / 100) * 0.099  # Maps 0→0.001, 100→0.1
```

**Files:** `src/ui/control_panel.py` lines ~391-405

---

#### Solution 4: Add Polynomial Degree Warning
**Priority:** 🟡 MEDIUM
**Effort:** 5 minutes
**Impact:** Prevents overfitting

**Implementation:**
```python
degree = st.slider(
    "Polynomial Degree",
    min_value=1,
    max_value=10,
    value=spectrum.processing_settings.baseline_degree,
    help="Controls baseline flexibility. Recommended: 2-3 for simple, 4-5 for complex."
)

# Warning for high degrees
if degree > 6:
    st.warning(
        f"⚠️ Degree {degree} may cause oscillations (Runge's phenomenon). "
        f"Consider using ALS instead for complex baselines."
    )
elif degree > 3:
    st.info(
        f"ℹ️ Degree {degree} is flexible. Check preview to ensure baseline doesn't fit through peaks."
    )
```

**Files:** `src/ui/control_panel.py` lines ~365-375

---

#### Solution 5: Enable Preview by Default
**Priority:** 🟡 MEDIUM
**Effort:** 1 minute
**Impact:** Better user feedback loop

**Change:**
```python
# Current:
show_preview = st.checkbox("Show Preview", value=False, ...)

# Proposed:
show_preview = st.checkbox("Show Preview", value=True, ...)  # Default ON
```

**Rationale:** Preview is essential for parameter tuning. Should be opt-out, not opt-in.

**Files:** `src/ui/control_panel.py` line ~359

---

#### Solution 6: Auto-Suggest Polynomial Degree (Use Existing Function!)
**Priority:** 🟢 LOW
**Effort:** 10 minutes
**Impact:** Better defaults for new users

**Implementation:**
```python
from ..processing.baseline import estimate_baseline_degree

# Calculate suggested degree
X = spectrum.processed_data.X
Y = spectrum.processed_data.Y
suggested_degree = estimate_baseline_degree(X, Y)

# Show suggestion to user
st.caption(f"💡 Suggested degree based on data: {suggested_degree}")

degree = st.slider(
    "Polynomial Degree",
    min_value=1,
    max_value=10,
    value=suggested_degree,  # Use suggestion as default!
    ...
)
```

**Files:** `src/ui/control_panel.py` lines ~365-375

---

### 6.2 MEDIUM-TERM ENHANCEMENTS (High Impact, Medium Effort)

#### Solution 7: Add Peak Masking / Region Exclusion
**Priority:** 🔴 HIGH
**Effort:** 2-3 hours
**Impact:** HUGE - solves overfitting problem directly

**Design:**

Allow users to define "exclusion zones" where baseline should interpolate, not fit.

**UI Mockup:**
```python
st.markdown("**Peak Exclusion Regions** (optional)")
st.caption("Define X ranges to exclude from baseline fitting (e.g., known peak locations)")

exclude_regions = st.text_area(
    "Exclusion Ranges",
    value="",
    placeholder="Example: 1300-1400, 1550-1620 (comma-separated)",
    help="Enter X ranges to exclude. Baseline will interpolate through these regions."
)

# Parse exclusion regions
exclusions = []
if exclude_regions.strip():
    for region in exclude_regions.split(','):
        try:
            x_min, x_max = map(float, region.split('-'))
            exclusions.append((x_min, x_max))
        except:
            st.error(f"Invalid region format: {region}. Use 'min-max' format.")
```

**Algorithm Modification:**

**Option A: Mask data before fitting**
```python
def baseline_polynomial_with_mask(x, y, degree, exclusions):
    """Polynomial baseline with excluded regions."""

    # Create mask (True = include in fit, False = exclude)
    mask = np.ones(len(x), dtype=bool)
    for x_min, x_max in exclusions:
        mask &= ~((x >= x_min) & (x <= x_max))

    # Fit polynomial only to masked data
    x_fit = x[mask]
    y_fit = y[mask]
    p = Polynomial.fit(x_fit, y_fit, degree)

    # Evaluate baseline over full range (interpolates through excluded regions)
    baseline = p(x)
    y_corrected = y - baseline

    return y_corrected, baseline
```

**Option B: Weighted fitting (more sophisticated)**
```python
def baseline_polynomial_with_weights(x, y, degree, exclusions):
    """Polynomial baseline with weighted regions."""

    # Create weights (1.0 = full weight, 0.0 = no weight)
    weights = np.ones(len(x))
    for x_min, x_max in exclusions:
        mask = (x >= x_min) & (x <= x_max)
        weights[mask] = 0.0  # Zero weight in excluded regions

    # Weighted polynomial fit
    p = Polynomial.fit(x, y, degree, w=weights)
    baseline = p(x)
    y_corrected = y - baseline

    return y_corrected, baseline
```

**For ALS:**
```python
def baseline_als_with_mask(x, y, lambda_, p, max_iter, exclusions):
    """ALS baseline with excluded regions."""

    # Create initial weights
    w = np.ones(len(y))

    # Set excluded regions to zero weight (permanent)
    for x_min, x_max in exclusions:
        mask = (x >= x_min) & (x <= x_max)
        w[mask] = 0.0  # Force zero weight

    # Rest of ALS algorithm with modified weight initialization
    for _ in range(max_iter):
        # ... (same as before, but excluded regions keep w=0)
```

**Impact:**
- ✅ Users can exclude known peak regions (D-band, G-band, etc.)
- ✅ Baseline interpolates smoothly through excluded zones
- ✅ Prevents overfitting into peaks
- ✅ Matches industry standard tools (Bruker OPUS, LabSpec)

**Files to Modify:**
1. `src/processing/baseline.py` - Add mask parameter to functions
2. `src/ui/control_panel.py` - Add exclusion UI
3. `src/models/spectrum.py` - Add `baseline_exclusions: List[Tuple[float, float]]` to ProcessingSettings

**Estimated Time:** 2-3 hours (implementation + testing)

---

#### Solution 8: Add Alternative Baseline Algorithms
**Priority:** 🟡 MEDIUM
**Effort:** 4-6 hours per algorithm
**Impact:** Better results for complex spectra

**Proposed Additions:**

**A. Rolling Ball (Morphological Baseline)**
- Simulates rolling a "ball" of radius `r` under the spectrum
- Baseline = top of ball trajectory
- Excellent for spectra with many sharp peaks
- Simple, intuitive parameter (ball radius in X units)

**Algorithm:**
```python
def baseline_rolling_ball(x, y, radius):
    """Rolling ball baseline (morphological opening)."""
    from scipy.ndimage import grey_opening

    # Convert radius to data points
    dx = np.median(np.diff(x))
    ball_size = int(radius / dx)

    # Morphological opening (erosion + dilation)
    baseline = grey_opening(y, size=ball_size)
    y_corrected = y - baseline

    return y_corrected, baseline
```

**B. Spline Baseline (Piecewise Polynomials)**
- Divide X range into segments, fit cubic splines
- Local control, no global oscillations
- Parameter: number of knots (breakpoints)

**Algorithm:**
```python
def baseline_spline(x, y, n_knots=10):
    """Piecewise cubic spline baseline."""
    from scipy.interpolate import UnivariateSpline

    # Fit smoothing spline with specified knots
    spline = UnivariateSpline(x, y, k=3, s=len(x) * np.var(y))
    baseline = spline(x)
    y_corrected = y - baseline

    return y_corrected, baseline
```

**C. Adaptive Iteratively Reweighted Penalized Least Squares (airPLS)**
- Improved ALS that adapts weights automatically
- Reference: Zhang et al. (2010), Analyst 135:1138
- No manual p parameter (self-optimizing)

**Algorithm (simplified):**
```python
def baseline_airpls(x, y, lambda_=1e5, max_iter=15):
    """Adaptive Iteratively Reweighted PLS."""
    # Similar to ALS but adaptive weight formula:
    # w_i = 0 if y_i > z_i + σ
    # w_i = exp(-k * (y_i - z_i)^2 / σ^2) if y_i ≤ z_i
    # (self-adjusting asymmetry based on residuals)
```

**UI Integration:**
```python
baseline_alg = st.radio(
    "Algorithm",
    ["Polynomial", "ALS", "Rolling Ball", "Spline", "airPLS"],
    help=(
        "Polynomial: Fast, simple (degree 2-3)\n"
        "ALS: Good for fluorescence (tune λ and p)\n"
        "Rolling Ball: Excellent for many sharp peaks\n"
        "Spline: Local control, no oscillations\n"
        "airPLS: Self-optimizing ALS (advanced)"
    )
)
```

**Estimated Time:**
- Rolling Ball: 2 hours (simple algorithm)
- Spline: 3 hours (parameter tuning)
- airPLS: 6 hours (complex weight adaptation)

---

#### Solution 9: Add Baseline Quality Metrics
**Priority:** 🟢 LOW
**Effort:** 1-2 hours
**Impact:** Helps users assess baseline quality objectively

**Metrics to Display:**

1. **Residual Standard Deviation:**
   ```python
   residuals = y - baseline
   residual_std = np.std(residuals)
   st.metric("Residual Std Dev", f"{residual_std:.2f}")
   ```

2. **Baseline Roughness (Curvature):**
   ```python
   d2_baseline = np.diff(baseline, n=2)  # 2nd derivative
   roughness = np.sum(d2_baseline**2)
   st.metric("Baseline Roughness", f"{roughness:.2e}")
   ```

3. **Fraction of Points Above Baseline:**
   ```python
   frac_above = np.mean(y > baseline)
   st.metric("Points Above Baseline", f"{frac_above*100:.1f}%")
   ```
   - **Expected:** ~50% for good baseline (passes through middle)
   - **Warning:** >70% suggests baseline is too low
   - **Warning:** <30% suggests baseline is too high (overfitting)

**Display in UI:**
```python
if show_preview:
    # ... (compute baseline)

    st.markdown("**Baseline Quality Metrics**")
    col1, col2, col3 = st.columns(3)

    with col1:
        residual_std = np.std(y - baseline_preview)
        st.metric("Residual σ", f"{residual_std:.1f}")

    with col2:
        roughness = np.sum(np.diff(baseline_preview, n=2)**2)
        st.metric("Roughness", f"{roughness:.2e}")

    with col3:
        frac_above = np.mean(Y > baseline_preview) * 100
        st.metric("Above Baseline", f"{frac_above:.0f}%")
        if frac_above > 70:
            st.caption("⚠️ Too low")
        elif frac_above < 30:
            st.caption("⚠️ Too high (overfit?)")
```

---

### 6.3 LONG-TERM ENHANCEMENTS (Medium Impact, High Effort)

#### Solution 10: Machine Learning Baseline Prediction
**Priority:** 🟢 LOW
**Effort:** 40+ hours (research project)
**Impact:** Fully automated baseline correction

**Concept:**
- Train neural network on (spectrum, baseline) pairs
- Input: Raw spectrum → Output: Predicted baseline
- No parameter tuning required

**Challenges:**
- Requires large training dataset (1000+ labeled spectra)
- Generalization to different instruments/samples
- Model interpretability (black box)

**Not Recommended** unless project scales significantly.

---

#### Solution 11: Interactive Baseline Editing
**Priority:** 🟢 LOW
**Effort:** 20+ hours
**Impact:** Ultimate user control

**Concept:**
- User clicks on plot to define baseline anchor points
- Spline interpolates between points
- Real-time visual feedback

**Implementation:**
- Requires Plotly click events in Streamlit
- Complex state management (anchor points, undo/redo)
- May conflict with existing preview system

**Example (pseudo-code):**
```python
# Capture click events on plot
if 'baseline_points' not in st.session_state:
    st.session_state['baseline_points'] = []

# Plotly click event handler (JavaScript injection)
st.markdown("""
<script>
document.addEventListener('plotly_click', function(data) {
    const x = data.points[0].x;
    const y = data.points[0].y;
    // Send to Streamlit session state
});
</script>
""", unsafe_allow_html=True)

# Fit spline through user points
if len(st.session_state['baseline_points']) >= 3:
    from scipy.interpolate import interp1d
    points_x = [p[0] for p in st.session_state['baseline_points']]
    points_y = [p[1] for p in st.session_state['baseline_points']]
    baseline_func = interp1d(points_x, points_y, kind='cubic')
    baseline = baseline_func(x)
```

**Complexity:** High (Plotly + Streamlit interaction is fragile)

---

## 7. Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
**Goal:** Fix bugs and improve parameter usability

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Fix lambda slider max (1e7→1e6) | 🔴 HIGH | 5 min | High | ⏳ TODO |
| Add log-scale lambda slider | 🔴 HIGH | 15 min | Very High | ⏳ TODO |
| Rephrase asymmetry parameter | 🟡 MEDIUM | 2 min | Medium | ⏳ TODO |
| Add polynomial degree warning | 🟡 MEDIUM | 5 min | Medium | ⏳ TODO |
| Enable preview by default | 🟡 MEDIUM | 1 min | Medium | ⏳ TODO |
| Auto-suggest polynomial degree | 🟢 LOW | 10 min | Low | ⏳ TODO |

**Total Effort:** ~40 minutes
**Expected Outcome:** Much better user experience with existing algorithms

---

### Phase 2: Peak Masking Feature (Week 2)
**Goal:** Solve overfitting problem with region exclusion

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Add exclusion UI (text area) | 🔴 HIGH | 30 min | Very High | ⏳ TODO |
| Modify polynomial function for masking | 🔴 HIGH | 1 hour | Very High | ⏳ TODO |
| Modify ALS function for masking | 🔴 HIGH | 1 hour | Very High | ⏳ TODO |
| Add exclusion to ProcessingSettings | 🔴 HIGH | 15 min | Medium | ⏳ TODO |
| Test with real spectra | 🟡 MEDIUM | 30 min | High | ⏳ TODO |

**Total Effort:** ~3 hours
**Expected Outcome:** Users can exclude peak regions, preventing overfitting

---

### Phase 3: Alternative Algorithms (Week 3-4)
**Goal:** Provide better baseline options for complex spectra

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Implement Rolling Ball baseline | 🟡 MEDIUM | 2 hours | High | ⏳ TODO |
| Implement Spline baseline | 🟡 MEDIUM | 3 hours | Medium | ⏳ TODO |
| Implement airPLS baseline | 🟢 LOW | 6 hours | Medium | ⏳ TODO |
| Update UI for algorithm selection | 🟡 MEDIUM | 30 min | Medium | ⏳ TODO |
| Document new algorithms | 🟢 LOW | 1 hour | Low | ⏳ TODO |

**Total Effort:** ~12.5 hours
**Expected Outcome:** More robust baseline correction for diverse spectra

---

### Phase 4: Quality Metrics & Refinement (Week 5)
**Goal:** Help users assess baseline quality

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Add residual std metric | 🟢 LOW | 30 min | Medium | ⏳ TODO |
| Add roughness metric | 🟢 LOW | 30 min | Low | ⏳ TODO |
| Add "fraction above" metric | 🟡 MEDIUM | 30 min | Medium | ⏳ TODO |
| Add quality warnings (too low/high) | 🟡 MEDIUM | 30 min | Medium | ⏳ TODO |

**Total Effort:** ~2 hours
**Expected Outcome:** Users can objectively evaluate baseline quality

---

## Summary & Recommendations

### IMMEDIATE ACTIONS (Do This Now)
1. ✅ **Fix lambda slider bug** (max=1e6, not 1e7) - 5 minutes
2. ✅ **Switch to log-scale lambda slider** - 15 minutes
3. ✅ **Enable preview by default** - 1 minute

**Total:** 21 minutes to dramatically improve user experience

---

### HIGH-PRIORITY FEATURES (Next Sprint)
1. ✅ **Peak masking/exclusion** - 3 hours, solves overfitting problem
2. ✅ **Rephrase asymmetry parameter** - 2 minutes, improves clarity
3. ✅ **Add polynomial degree warning** - 5 minutes, prevents overfitting

**Total:** ~3 hours to address core user complaints

---

### MEDIUM-PRIORITY ENHANCEMENTS (Future Sprints)
1. **Rolling Ball baseline** - 2 hours, excellent for peak-heavy spectra
2. **Baseline quality metrics** - 2 hours, objective assessment
3. **Spline baseline** - 3 hours, local control without oscillations

---

### Technical Debt to Address
- [ ] UI slider ranges must match validation ranges (lambda bug)
- [ ] `estimate_baseline_degree()` exists but is never called (use it!)
- [ ] No convergence monitoring for ALS (add warning if max_iter reached)
- [ ] No unit tests for baseline functions (add test suite)

---

### Key Takeaways

**Root Cause of User Issues:**
1. **Overfitting:** Algorithms treat peaks as data to fit, not features to avoid
2. **Parameter Intuitiveness:** Lambda is logarithmic but slider is linear
3. **Lack of Guidance:** No warnings, suggestions, or quality metrics

**Best Solutions:**
1. **Short-term:** Log-scale lambda slider + peak masking
2. **Medium-term:** Rolling Ball algorithm + quality metrics
3. **Long-term:** Interactive baseline editing (if user demand justifies effort)

---

**End of Algorithm Analysis**
