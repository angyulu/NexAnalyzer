# Research: SpectralFit Technical Decisions

**Date**: 2025-12-13
**Phase**: 0 (Outline & Research)
**Prerequisites**: spec.md, plan.md

## Overview

This document consolidates research findings for key technical decisions in SpectralFit. All decisions are informed by the PRD requirements, constitution principles, and best practices for scientific Python applications.

---

## R1: Web UI Framework Selection

### Decision: Streamlit

### Rationale

1. **Rapid Prototyping for Data Apps**: Streamlit specializes in interactive data science applications with minimal boilerplate. Entire UI can be built with Python (no separate HTML/CSS/JS).

2. **Built-in State Management**: `st.session_state` provides per-session persistence (critical for multi-file workflow where each file retains independent settings).

3. **Native Widget Support**: File uploader, sliders, dropdowns, checkboxes, data editors (editable tables for peak definitions) are first-class components.

4. **Plotly Integration**: Streamlit natively renders Plotly figures with full interactivity (zoom, pan, legend toggles).

5. **Single-User Desktop Deployment**: Streamlit runs a local server (`streamlit run app.py`) ideal for lab computers; no authentication/multi-user complexity needed.

6. **Performance**: Reruns only changed components (not entire page); meets <500ms interaction target for typical workflows.

### Alternatives Considered

- **Dash (Plotly)**: More flexible but requires explicit callback management and HTML layout (more complex than needed for linear workflow).
- **Jupyter Notebook/Voila**: Good for exploratory analysis but lacks robust UI components (no native editable tables, file management).
- **Flask/FastAPI + React**: Full-stack overkill for single-user desktop app; requires separate frontend build pipeline.
- **PyQt/Tkinter**: Native desktop GUI but poor integration with Plotly; harder to achieve publication-quality interactive plots.

### Implementation Notes

- Use `st.tabs()` for Pre-process / Fit / Export workflow sections (enforces linear navigation).
- Use `st.sidebar` for mode toggle, file upload, project I/O (persistent controls).
- Use `st.data_editor()` for editable peak table (FR-025, FR-026).
- Cache expensive operations with `@st.cache_data` (file parsing, baseline calculation) to avoid redundant computation on rerun.

---

## R2: Numerical Computing Stack

### Decision: NumPy + SciPy + lmfit

### Rationale

1. **NumPy**: Standard for array operations; all spectral data (X, Y) represented as `np.ndarray`. Handles negative Raman shifts naturally (FR-003).

2. **SciPy**:
   - `scipy.stats.median_abs_deviation`: Direct MAD calculation for modified Z-score (FR-011).
   - `scipy.signal.find_peaks`: Auto-detect peaks (FR-027, FR-028).
   - `scipy.polynomial.Polynomial`: Polynomial baseline fitting (FR-017).
   - `scipy.sparse` + `scipy.linalg.solve`: ALS baseline correction (FR-018) with banded matrix solver.

3. **lmfit**: Purpose-built for nonlinear least-squares fitting with parameter bounds and constraints.
   - `lmfit.models.VoigtModel`: Direct Voigt profile implementation (FR-031).
   - `lmfit.Parameters`: Easy bound specification (FR-029 auto-bounds).
   - Built-in Levenberg-Marquardt via `method='leastsq'` (FR-032).
   - Returns fit statistics (χ², R², covariance) directly (FR-036).

### Alternatives Considered

- **curve_fit (scipy.optimize)**: Lower-level than lmfit; requires manual Voigt function definition and lacks built-in fit quality metrics.
- **scikit-learn**: Machine learning focus; no specialized spectroscopy fitting models.
- **PyMC/emcee (Bayesian)**: Over-engineered for deterministic least-squares fitting; violates Principle V (simplicity).

### Implementation Notes

- **Modified Z-score** (de-spiking):
  ```python
  from scipy.stats import median_abs_deviation
  mad = median_abs_deviation(y, nan_policy='omit')
  z_scores = 0.6745 * (y - np.median(y)) / (mad + 1e-10)
  ```

- **ALS Baseline** (from Eilers & Boelens 2005):
  ```python
  from scipy.sparse import diags, csr_matrix
  from scipy.sparse.linalg import spsolve
  # Iterative weighted least squares with 2nd derivative penalty
  ```

- **Voigt Fitting**:
  ```python
  from lmfit.models import VoigtModel
  model = VoigtModel(prefix='p1_') + VoigtModel(prefix='p2_')
  params.add('p1_center', value=1350, min=1345, max=1355)  # Raman auto-bounds
  result = model.fit(y, params, x=x, method='leastsq')
  ```

---

## R3: Interactive Visualization

### Decision: Plotly

### Rationale

1. **Constitution Requirement**: Constitution explicitly mandates Plotly for interactive plots (Visualization section, line 88).

2. **Streamlit Native Support**: `st.plotly_chart()` renders Plotly figures with full interactivity retained.

3. **Subplot Support**: `plotly.subplots.make_subplots()` creates composite layout (3/4 top, 1/4 bottom residuals per FR-038).

4. **Legend Interactivity**: Built-in legend click-to-toggle for component visibility (FR-040).

5. **Export**: `.write_image()` for PNG (FR-048), `.write_html()` for standalone interactive HTML (FR-049).

6. **Styling Control**: Full control over colors, line styles, widths, markers (FR-043).

### Alternatives Considered

- **Matplotlib**: Standard scientific plotting but poor web interactivity (zoom/pan requires mplcursors plugin; no native legend toggles).
- **Bokeh**: Interactive but less Streamlit integration and heavier bundle size.
- **Altair**: Declarative grammar but limited low-level control for custom subplot layouts.

### Implementation Notes

- Use `plotly.graph_objects.Scatter` for data and fit curves (custom styling).
- Use `go.Layout` to enforce mode-aware axis labels (FR-041):
  ```python
  xaxis_title = "Raman Shift (cm⁻¹)" if mode == "Raman" else "Wavelength (nm)"
  ```
- Use `showlegend=True` + `visible='legendonly'` for initial component hiding.
- Cache plot generation with `@st.cache_data` for fast re-renders.

---

## R4: Data Persistence Strategy

### Decision: Session-based state (Streamlit session_state) + JSON export

### Rationale

1. **Constitution Requirement**: "Data retention is session-based (no server-side storage)" (Assumptions, line 251 in spec).

2. **Streamlit session_state**: Per-browser-tab dictionary that persists across Streamlit reruns (survives button clicks, slider changes) but clears on browser close/refresh.

3. **Multi-File Isolation**: Each uploaded file stores its own state dict in `st.session_state['files'][filename]`:
   ```python
   {
     'raw_x': np.array(...),
     'raw_y': np.array(...),
     'despike_y': np.array(...) or None,
     'baseline_y': np.array(...) or None,
     'baseline_params': {'algorithm': 'Polynomial', 'degree': 3},
     'peak_table': pd.DataFrame(...),
     'fit_result': lmfit.ModelResult or None
   }
   ```

4. **JSON Project Save/Load**: Serialize session_state to JSON (FR-051 to FR-055):
   - Convert `np.ndarray` → `list` (JSON-serializable).
   - Store peak table as list of dicts.
   - Exclude large arrays (raw_x/y) unless user opts in ("Include spectral data in project file" checkbox).
   - Load restores session_state from JSON; warns if .txt files missing.

### Alternatives Considered

- **SQLite database**: Overkill for single-user; adds complexity (schema migrations, connection management).
- **File-based pickle**: Python-specific; breaks cross-version compatibility; security risk (arbitrary code execution).
- **Cloud storage (S3, GCS)**: Violates single-user desktop assumption; requires network, credentials.

### Implementation Notes

- Use `@st.cache_data` for file parsing (avoid re-parsing on every rerun).
- JSON schema versioning (FR-055):
  ```json
  {
    "version": "1.0.0",
    "timestamp": "2025-12-13T14:30:00Z",
    "files": [{"filename": "sample.txt", "mode": "Raman", ...}]
  }
  ```

---

## R5: File Parsing & Delimiter Detection

### Decision: Pandas with custom validation

### Rationale

1. **Pandas `read_csv()`**: Handles tab/comma delimiters, scientific notation, configurable column parsing.

2. **Auto-delimiter detection**: `pd.read_csv(sep=None, engine='python')` auto-detects tab vs comma (FR-002).

3. **Robust error handling**: Pandas skips malformed rows with `on_bad_lines='skip'` and returns warnings (FR-004).

4. **Validation logic**:
   - Check exactly 2 columns (FR-001).
   - Check all numeric (coerce with `pd.to_numeric(..., errors='coerce')` then drop NaNs).
   - Check no headers (reject if first row non-numeric).

### Alternatives Considered

- **NumPy `loadtxt()`/`genfromtxt()`**: Simpler but less robust error handling; no auto-delimiter detection.
- **CSV module (stdlib)**: Requires manual type coercion and validation; more boilerplate.

### Implementation Notes

```python
import pandas as pd

def parse_spectrum(file):
    try:
        df = pd.read_csv(file, sep=None, header=None, engine='python')
        if df.shape[1] != 2:
            raise ValueError(f"Expected 2 columns, found {df.shape[1]}")
        df = df.apply(pd.to_numeric, errors='coerce')
        original_rows = len(df)
        df = df.dropna()
        if len(df) < original_rows:
            st.warning(f"Skipped {original_rows - len(df)} non-numeric rows")
        return df[0].values, df[1].values  # X, Y as np.ndarray
    except Exception as e:
        st.error(f"File parsing failed: {e}")
        return None, None
```

---

## R6: Performance Optimization

### Decision: Algorithm selection + Streamlit caching

### Rationale

1. **Algorithm Complexity**:
   - Modified Z-score: O(n) for median + MAD calculation → <100ms for 10k points.
   - Polynomial baseline: O(n²) for least squares → <200ms for degree 5.
   - ALS baseline: O(n × iter) with sparse matrix solver → ~500ms for λ=10⁴, 10 iterations.
   - Voigt fitting (lmfit): O(peaks × iter × n) → 1-2s for 5 peaks, 50 L-M iterations.

2. **Streamlit Caching**:
   - Cache file parsing with `@st.cache_data` (avoid re-reading on every widget change).
   - Cache baseline calculation (expensive ALS) until parameters change.
   - Do NOT cache fitting (user expects fresh fit on "Run Fit" button click).

3. **Data Size Limits**:
   - Optimized for 1k-10k points (SC-002: 1-3s).
   - Graceful degradation for 10k-20k points (SC-007: <500ms interaction).
   - Warn if >20k points: "Large spectrum detected; performance may be reduced."

### Alternatives Considered

- **Numba JIT compilation**: Adds dependency; minimal gain for vectorized NumPy/SciPy operations.
- **Multiprocessing**: Overkill for single-spectrum operations; Streamlit rerun overhead > parallelism gain.
- **Cython/C extensions**: Premature optimization; Python implementation meets targets.

### Implementation Notes

- Profile with `cProfile` if performance targets not met.
- Use `st.spinner("Fitting in progress...")` during long operations (FR-034).

---

## R7: Testing Strategy

### Decision: pytest + Streamlit AppTest

### Rationale

1. **pytest**: Standard Python testing framework; supports fixtures, parametrization, coverage reporting.

2. **Streamlit AppTest** (st.testing): Test Streamlit UI components in isolation:
   - Simulate button clicks, slider changes, file uploads.
   - Assert widget states and outputs.
   - Example: Test "Reset to Raw" button restores original data.

3. **Test Pyramid**:
   - **Unit tests** (majority): Test individual algorithms (despiking, baseline, fitting) with known inputs/outputs.
   - **Integration tests**: Test full workflow (load → despike → baseline → fit → export) with sample .txt files.
   - **Contract tests**: Validate JSON project schema (save → load round-trip).

### Alternatives Considered

- **unittest (stdlib)**: More verbose than pytest; lacks fixtures and parametrization.
- **Hypothesis (property-based)**: Useful for numerical edge cases but overkill for this application.

### Implementation Notes

- **Fixtures** in `tests/fixtures/`:
  - `sample_raman.txt`: 3 Gaussian peaks + noise + 2 spikes.
  - `sample_pl.txt`: 2 overlapping peaks + fluorescence background.

- **Unit test example** (despiking):
  ```python
  def test_modified_zscore():
      y = np.array([1, 2, 3, 100, 5])  # 100 is spike
      y_clean, mask = remove_spikes(y, threshold=3.5)
      assert mask[3] == True  # spike detected
      assert y_clean[3] == np.median([2, 3, 5])  # replaced with median
  ```

- **Integration test example**:
  ```python
  def test_full_workflow():
      x, y = parse_spectrum('fixtures/sample_raman.txt')
      y_despike, _ = remove_spikes(y, threshold=6.0)
      y_baseline, bl = baseline_polynomial(x, y_despike, degree=2)
      result = fit_voigt(x, y_baseline, peaks=[1350, 1580])
      assert result.success
      assert result.params['p1_center'].value == pytest.approx(1350, abs=10)
  ```

---

## R8: Deployment & Distribution

### Decision: Local Streamlit server + pip-installable package (optional)

### Rationale

1. **Primary deployment**: Researchers run `streamlit run app.py` locally on their lab computer.

2. **Distribution**:
   - **Option A** (simple): ZIP archive with `app.py`, `src/`, `requirements.txt`; user runs `pip install -r requirements.txt && streamlit run app.py`.
   - **Option B** (polished): Package as pip-installable (`setup.py` or `pyproject.toml`) with entry point: `spectralfit` CLI command that launches Streamlit.

3. **No server hosting needed**: Single-user assumption eliminates need for cloud deployment, SSL, authentication.

### Alternatives Considered

- **Docker container**: Adds complexity; requires Docker installation on lab computers.
- **PyInstaller/cx_Freeze (standalone binary)**: Streamlit doesn't bundle well into single executable; large binary size.
- **Web hosting (Streamlit Cloud, Heroku)**: Inappropriate for session-based, local-file-only app.

### Implementation Notes

- Document installation steps in `README.md`:
  ```bash
  pip install spectralfit  # or git clone + pip install -e .
  spectralfit              # launches Streamlit app
  ```

---

## Summary Table

| Research Item | Decision | Key Rationale |
|---------------|----------|---------------|
| R1: Web UI Framework | Streamlit | Rapid prototyping, native state management, Plotly integration |
| R2: Numerical Computing | NumPy + SciPy + lmfit | Standard scientific stack, Voigt profiles, bounded fitting |
| R3: Visualization | Plotly | Constitution requirement, interactivity, export support |
| R4: Data Persistence | session_state + JSON | Session-based per constitution, JSON for project save/load |
| R5: File Parsing | Pandas `read_csv()` | Auto-delimiter detection, robust error handling |
| R6: Performance | Algorithm selection + caching | Meets 1-3s targets, Streamlit `@st.cache_data` |
| R7: Testing | pytest + Streamlit AppTest | Unit/integration tests, UI component testing |
| R8: Deployment | Local Streamlit server | Single-user desktop, no hosting infrastructure |

---

## Next Steps

Proceed to **Phase 1: Design & Contracts**:
- Generate `data-model.md` (entities: Spectrum, Peak, FitResult, ProjectState).
- Generate `contracts/state-schema.json` (JSON project file schema).
- Generate `quickstart.md` (developer onboarding guide).
- Update agent context with technology stack.
