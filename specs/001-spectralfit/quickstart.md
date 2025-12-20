# Quickstart: SpectralFit Development

**Date**: 2025-12-13
**Target Audience**: Developers implementing SpectralFit
**Prerequisites**: Python 3.10+, git, basic knowledge of Streamlit and NumPy

## Overview

This guide helps developers set up the SpectralFit development environment, understand the codebase structure, and make their first contribution. For architectural details, see `plan.md` and `data-model.md`.

---

## 1. Environment Setup

### Clone and Install

```bash
# Clone repository
git clone <repo-url>
cd Spectrum_Analyzer/SpectralFit

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # pytest, black, mypy, etc.
```

### Required Dependencies (`requirements.txt`)

```
streamlit>=1.28.0
numpy>=1.24.0
scipy>=1.11.0
lmfit>=1.2.0
plotly>=5.17.0
pandas>=2.0.0
```

### Development Dependencies (`requirements-dev.txt`)

```
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.9.0
mypy>=1.5.0
ruff>=0.0.290
```

---

## 2. Project Structure

```
SpectralFit/
├── app.py                    # Streamlit entry point (run this)
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── src/                      # All application logic
│   ├── models/               # Data models (Spectrum, Peak, FitResult)
│   ├── processing/           # Algorithms (despiking, baseline, fitting)
│   ├── visualization/        # Plotly plotting
│   ├── io/                   # Export (CSV, PNG, HTML) and project save/load
│   └── ui/                   # Streamlit UI components
└── tests/                    # pytest test suite
    ├── unit/
    ├── integration/
    └── fixtures/             # Sample .txt spectra for testing
```

**Key Entry Points**:
- `app.py`: Streamlit application entry (`streamlit run app.py`)
- `src/models/spectrum.py`: Core data structures
- `src/processing/fitting.py`: Voigt fitting logic (lmfit)
- `src/ui/fit_tab.py`: Peak table and "Run Fit" button UI

---

## 3. Running the Application

### Local Development Server

```bash
streamlit run app.py
```

- Opens browser at `http://localhost:8501`
- Auto-reloads on file changes (edit `src/*.py`, refresh browser)
- Session state persists until browser tab closed

### Test with Sample Data

```bash
# Generate sample Raman spectrum (if not in fixtures/)
python scripts/generate_sample_spectrum.py --mode raman --peaks 3 --output tests/fixtures/sample_raman.txt

# Run app and upload tests/fixtures/sample_raman.txt
streamlit run app.py
```

---

## 4. Core Concepts

### 4.1 Session State Management

All application state is stored in `st.session_state` (Streamlit's per-tab dictionary).

**Structure**:
```python
st.session_state = {
    'mode': 'Raman',  # or 'PL'
    'current_file': 'sample_raman.txt',  # Selected file
    'files': {
        'sample_raman.txt': SpectrumFile(...),
        'sample_pl.txt': SpectrumFile(...)
    },
    'global_styling': StylingPreferences(...)
}
```

**Accessing State**:
```python
# In any UI module (src/ui/*.py)
if 'files' not in st.session_state:
    st.session_state['files'] = {}

current_file = st.session_state.get('current_file')
spectrum = st.session_state['files'].get(current_file)
```

### 4.2 Data Model

See `data-model.md` for full details. Key classes:

- **SpectrumFile**: Container for a single .txt file's data and processing state
- **SpectrumData**: Immutable X/Y array pair (with validation)
- **ProcessingSettings**: De-spike and baseline parameters
- **PeakDefinition**: User-defined peak guess (for fitting)
- **FitResult**: Fitted parameters, quality metrics, error messages

**Example**:
```python
from src.models.spectrum import SpectrumFile, SpectrumData, ProcessingSettings

# Create new spectrum
spectrum = SpectrumFile(
    filename="test.txt",
    mode="Raman",
    raw_data=SpectrumData(X=x_array, Y=y_array),
    processed_data=SpectrumData(X=x_array, Y=y_array),
    processing_settings=ProcessingSettings(),
    peak_table=[],
    fit_result=None
)
```

### 4.3 Linear Workflow

The application enforces a strict processing order:

1. **Data Ingestion** (sidebar): Upload .txt → parse → create SpectrumFile
2. **Pre-process Tab**:
   - De-spike: Modify `spectrum.processed_data.Y` (keep X unchanged)
   - Baseline: Subtract baseline from `spectrum.processed_data.Y`
3. **Fit Tab**:
   - Populate peak table → Run fit → Store FitResult
4. **Export Tab**:
   - Visualize fit + components + residuals
   - Export CSV/PNG/HTML

**Reset to Raw** button reverts `spectrum.processed_data` to `spectrum.raw_data` and clears `spectrum.fit_result`.

### 4.4 Mode-Aware Behavior

Mode (`"Raman"` or `"PL"`) affects:

- **Axis labels**: "Raman Shift (cm⁻¹)" vs "Wavelength (nm)"
- **Auto-bounds** (FR-029):
  - Raman: center ± 5 cm⁻¹
  - PL: center ± 30 nm
- **Default ALS parameters** (optional future enhancement)

**Implementation**:
```python
mode = st.session_state['mode']
if mode == "Raman":
    center_tolerance = 5.0  # cm⁻¹
    x_label = "Raman Shift (cm⁻¹)"
else:  # PL
    center_tolerance = 30.0  # nm
    x_label = "Wavelength (nm)"
```

---

## 5. Development Workflow

### 5.1 Adding a New Feature

**Example**: Add "Export Baseline" button

1. **Plan** (if non-trivial):
   - Check constitution compliance (does it fit Principles I-V?)
   - Update `plan.md` if architectural

2. **Write Test First** (TDD per Constitution Principle III):
   ```python
   # tests/unit/test_export.py
   def test_export_baseline_csv():
       x = np.linspace(0, 1000, 100)
       y_baseline = x * 0.1 + 5
       csv_str = export_baseline_csv(x, y_baseline)
       assert "X,Y" in csv_str  # Check header
       assert len(csv_str.splitlines()) == 101  # Header + 100 rows
   ```

3. **Implement**:
   ```python
   # src/io/export.py
   def export_baseline_csv(x: np.ndarray, y: np.ndarray) -> str:
       df = pd.DataFrame({'X': x, 'Y': y})
       return df.to_csv(index=False)
   ```

4. **Add UI Component**:
   ```python
   # src/ui/preprocess_tab.py (in baseline section)
   if st.button("Export Baseline"):
       csv = export_baseline_csv(spectrum.processed_data.X, baseline_curve)
       st.download_button("Download", csv, file_name="baseline.csv")
   ```

5. **Test Manually**: `streamlit run app.py`, upload spectrum, click "Export Baseline"

6. **Run Automated Tests**:
   ```bash
   pytest tests/unit/test_export.py::test_export_baseline_csv
   pytest tests/integration/  # Full workflow tests
   ```

### 5.2 Debugging Tips

**Streamlit-Specific**:
- Use `st.write(variable)` to inspect state (appears in UI)
- Use `st.session_state` inspector in browser DevTools (Streamlit debug mode)
- Clear session state: Close and reopen browser tab

**Algorithm Debugging**:
- Add print statements in `src/processing/*.py` (output appears in terminal running `streamlit run`)
- Use `import pdb; pdb.set_trace()` for breakpoints
- Test algorithms in isolation with pytest:
  ```bash
  pytest tests/unit/test_fitting.py -v -s  # -s shows print output
  ```

**Performance Profiling**:
```python
import cProfile
import pstats

with cProfile.Profile() as pr:
    result = fit_voigt_peaks(x, y, peak_table)

stats = pstats.Stats(pr)
stats.sort_stats('cumtime')
stats.print_stats(10)  # Top 10 slowest functions
```

---

## 6. Testing

### 6.1 Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage
```

### 6.2 Test Fixtures

Sample spectra in `tests/fixtures/`:

- `sample_raman.txt`: 3 Gaussian peaks (D, G, 2D bands) + Gaussian noise + 2 spikes
- `sample_pl.txt`: 2 overlapping peaks + exponential fluorescence background

**Usage**:
```python
import pytest
from src.processing.parser import parse_spectrum

@pytest.fixture
def raman_spectrum():
    x, y = parse_spectrum('tests/fixtures/sample_raman.txt')
    return x, y

def test_despiking(raman_spectrum):
    x, y = raman_spectrum
    y_clean, mask = remove_spikes(y, threshold=6.0)
    assert mask.sum() == 2  # Expect 2 spikes detected
```

### 6.3 Testing Streamlit Components

Use `streamlit.testing.v1.AppTest`:

```python
from streamlit.testing.v1 import AppTest

def test_mode_toggle():
    at = AppTest.from_file("app.py")
    at.run()

    # Check initial mode
    assert at.session_state['mode'] == 'Raman'

    # Toggle to PL
    at.radio('mode').set_value('PL').run()
    assert at.session_state['mode'] == 'PL'
```

---

## 7. Code Style & Conventions

### 7.1 Formatting

Use **Black** (auto-formatter):
```bash
black src/ tests/
```

### 7.2 Linting

Use **Ruff** (fast linter):
```bash
ruff check src/ tests/
ruff check src/ tests/ --fix  # Auto-fix issues
```

### 7.3 Type Hints

Use **mypy** (type checker):
```python
# Good: Type-hinted function
def remove_spikes(y: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    ...

# Run mypy
mypy src/
```

### 7.4 Docstrings

Use **NumPy-style docstrings**:

```python
def baseline_polynomial(x: np.ndarray, y: np.ndarray, degree: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Fit and subtract polynomial baseline from spectrum.

    Parameters
    ----------
    x : np.ndarray
        Wavenumber or wavelength array.
    y : np.ndarray
        Intensity array (raw or de-spiked).
    degree : int
        Polynomial degree (1-10).

    Returns
    -------
    y_corrected : np.ndarray
        Baseline-corrected intensity.
    baseline : np.ndarray
        Fitted baseline curve.

    References
    ----------
    scipy.polynomial.Polynomial.fit
    """
    from scipy.polynomial import Polynomial
    p = Polynomial.fit(x, y, degree)
    baseline = p(x)
    return y - baseline, baseline
```

---

## 8. Common Tasks

### 8.1 Add a New Algorithm

**Example**: Add Savitzky-Golay smoothing to pre-processing

1. **Research** (update `research.md`):
   - Decision: scipy.signal.savgol_filter
   - Rationale: Standard smoothing for spectroscopy, preserves peak shapes
   - Alternatives: Gaussian filter (oversmooths), moving average (artifacts)

2. **Implement in `src/processing/smoothing.py`**:
   ```python
   from scipy.signal import savgol_filter

   def smooth_savgol(y: np.ndarray, window_length: int, polyorder: int) -> np.ndarray:
       """Apply Savitzky-Golay filter..."""
       return savgol_filter(y, window_length, polyorder)
   ```

3. **Add UI Control in `src/ui/preprocess_tab.py`**:
   ```python
   if st.checkbox("Apply Savitzky-Golay Smoothing"):
       window = st.slider("Window Length", 5, 51, 11, step=2)  # Must be odd
       polyorder = st.slider("Polynomial Order", 1, 5, 2)
       spectrum.processed_data.Y = smooth_savgol(spectrum.processed_data.Y, window, polyorder)
   ```

4. **Test**:
   ```python
   # tests/unit/test_smoothing.py
   def test_savgol_reduces_noise():
       y_noisy = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
       y_smooth = smooth_savgol(y_noisy, window_length=11, polyorder=2)
       assert np.std(y_smooth) < np.std(y_noisy)  # Smoothing reduces variance
   ```

### 8.2 Add Export Format

**Example**: Add Excel (.xlsx) export

1. **Add dependency**:
   ```bash
   pip install openpyxl
   echo "openpyxl>=3.1.0" >> requirements.txt
   ```

2. **Implement in `src/io/export.py`**:
   ```python
   def export_master_excel(files: dict, output_path: str):
       """Export fitted peaks to Excel with one sheet per file."""
       with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
           for filename, spectrum in files.items():
               if spectrum.fit_result:
                   df = fit_result_to_dataframe(spectrum.fit_result)
                   df.to_excel(writer, sheet_name=filename[:31], index=False)  # Sheet name max 31 chars
   ```

3. **Add UI Button in `src/ui/export_tab.py`**:
   ```python
   if st.button("Download Excel"):
       buffer = io.BytesIO()
       export_master_excel(st.session_state['files'], buffer)
       st.download_button("Download", buffer.getvalue(), file_name="spectralfit_export.xlsx")
   ```

### 8.3 Debug a Fit Convergence Failure

1. **Reproduce Issue**:
   - Upload problematic spectrum
   - Note peak table settings

2. **Isolate in Unit Test**:
   ```python
   def test_failing_fit():
       x, y = load_problematic_spectrum()  # Save as fixture
       peak_table = [PeakDefinition(center=1350, amplitude=500, width_fwhm=50)]
       result = fit_voigt_peaks(x, y, peak_table)
       assert result.success  # This will fail, showing error message
   ```

3. **Debug lmfit**:
   ```python
   # In src/processing/fitting.py
   result = model.fit(y, params, x=x, method='leastsq', verbose=True)  # Add verbose=True
   print(result.fit_report())  # Shows parameter evolution, chi-squared history
   ```

4. **Common Fixes**:
   - **Bad initial guess**: Center far from actual peak → Use auto-find or manual inspection
   - **Bounds too tight**: Widen center_min/max or width_min/max
   - **Too many peaks**: Reduce peak count (overlapping peaks may confuse fitter)
   - **Noisy data**: Apply smoothing before fitting

---

## 9. Release Checklist

Before tagging a version:

- [ ] All tests pass (`pytest`)
- [ ] Code formatted (`black src/ tests/`)
- [ ] No lint errors (`ruff check src/ tests/`)
- [ ] Type checks pass (`mypy src/`)
- [ ] Constitution compliance verified (check `plan.md` gates)
- [ ] `README.md` updated with new features
- [ ] `CHANGELOG.md` updated (if exists)
- [ ] Version bumped in `setup.py` or `pyproject.toml`
- [ ] Git tag created: `git tag -a v1.0.0 -m "Release 1.0.0"`

---

## 10. Troubleshooting

### Issue: Streamlit session state lost on refresh

**Cause**: Browser refresh clears `st.session_state`.

**Solution**: Save project to JSON before refresh, reload after.

### Issue: Plot rendering slow (>500ms)

**Causes**:
1. Too many data points (>20k)
2. Too many peak components (>10)
3. Not using `@st.cache_data`

**Solutions**:
1. Downsample data for plotting (keep full resolution for fitting)
2. Limit peak count to 10 (warn user)
3. Cache plot generation:
   ```python
   @st.cache_data
   def generate_plot(x, y, fit_result):
       ...
   ```

### Issue: lmfit fitting hangs

**Causes**:
1. Extremely poor initial guess (fitter exploring parameter space)
2. Too many peaks (combinatorial explosion)

**Solutions**:
1. Add timeout:
   ```python
   import signal
   signal.alarm(5)  # 5-second timeout
   try:
       result = model.fit(...)
   except Exception:
       st.error("Fit timed out. Try fewer peaks or better guesses.")
   finally:
       signal.alarm(0)
   ```
2. Limit peak count to 5-10

---

## 11. Further Reading

- **Streamlit Docs**: https://docs.streamlit.io
- **lmfit Docs**: https://lmfit.github.io/lmfit-py/
- **Plotly Docs**: https://plotly.com/python/
- **Constitution**: `.specify/memory/constitution.md`
- **Architecture**: `specs/001-spectralfit/plan.md`
- **Data Model**: `specs/001-spectralfit/data-model.md`

---

**Next Steps**: Read `plan.md` for architectural overview, then dive into `src/models/` to understand data structures.
