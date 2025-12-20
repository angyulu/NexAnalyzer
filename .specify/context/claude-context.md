# Claude Agent Context: SpectralFit

**Last Updated**: 2025-12-13
**Auto-generated** from feature plans by `/speckit.plan`

## Active Technologies

### Language & Runtime
- **Python 3.10+**: Primary language
- **Streamlit 1.28+**: Web UI framework for interactive data applications

### Core Dependencies
- **NumPy 1.24+**: Array operations, numerical computing
- **SciPy 1.11+**: Scientific computing (stats, signal processing, polynomial, sparse matrices)
- **lmfit 1.2+**: Nonlinear least-squares fitting with parameter bounds
- **Plotly 5.17+**: Interactive plotting and visualization
- **Pandas 2.0+**: Data handling and CSV export

### Development Tools
- **pytest 7.4+**: Unit and integration testing
- **pytest-cov 4.1+**: Code coverage reporting
- **black 23.9+**: Code auto-formatter
- **mypy 1.5+**: Static type checking
- **ruff 0.0.290+**: Fast Python linter

## Project Structure

```
SpectralFit/
├── app.py                    # Streamlit entry point
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── src/
│   ├── models/               # Data models (Spectrum, Peak, FitResult)
│   ├── processing/           # Algorithms (despiking, baseline, fitting)
│   ├── visualization/        # Plotly plotting
│   ├── io/                   # Export and project save/load
│   └── ui/                   # Streamlit UI components
└── tests/
    ├── unit/                 # Unit tests
    ├── integration/          # Integration tests
    └── fixtures/             # Sample .txt spectra
```

## Commands

### Development
```bash
# Run local development server
streamlit run app.py

# Run tests
pytest                        # All tests
pytest tests/unit/            # Unit tests only
pytest tests/integration/     # Integration tests only
pytest --cov=src              # With coverage

# Code quality
black src/ tests/             # Format code
ruff check src/ tests/        # Lint
ruff check src/ tests/ --fix  # Lint and auto-fix
mypy src/                     # Type check
```

### Installation
```bash
# Development setup
python3.10 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Code Style

### Python Conventions
- **Formatter**: Black (line length 100, default settings)
- **Linter**: Ruff (configured for scientific Python)
- **Type Hints**: Required for all public functions (NumPy-style type hints)
- **Docstrings**: NumPy-style for all public functions

### Example
```python
import numpy as np
from typing import Tuple

def remove_spikes(
    y: np.ndarray, threshold: float = 6.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remove cosmic-ray spikes using modified Z-score (MAD-based).

    Parameters
    ----------
    y : np.ndarray
        Intensity array.
    threshold : float, default=6.0
        Modified Z-score threshold (3.0-15.0).

    Returns
    -------
    y_clean : np.ndarray
        Cleaned intensity (spikes replaced with local median).
    spike_mask : np.ndarray (bool)
        True at spike indices.

    References
    ----------
    Iglewicz & Hoaglin (1993), "How to Detect and Handle Outliers"
    """
    from scipy.stats import median_abs_deviation

    median_y = np.median(y)
    mad = median_abs_deviation(y, nan_policy='omit')
    z_scores = 0.6745 * (y - median_y) / (mad + 1e-10)
    spike_mask = np.abs(z_scores) > threshold

    y_clean = y.copy()
    for idx in np.where(spike_mask)[0]:
        neighbors = y[max(0, idx - 2) : min(len(y), idx + 3)]
        y_clean[idx] = np.median(neighbors)

    return y_clean, spike_mask
```

### Streamlit Conventions
- Use `st.session_state` for all persistent state
- Cache expensive operations with `@st.cache_data`
- Use `st.tabs()` for workflow sections (Pre-process, Fit, Export)
- Use `st.sidebar` for global controls (mode, file selector, project I/O)

### Data Model Conventions
- Immutable data structures where possible (SpectrumData uses frozen dataclass pattern)
- Validation in `__init__` methods
- Type hints for all fields
- `to_dict()` and `from_dict()` methods for JSON serialization

## Recent Changes

### Feature: 001-spectralfit (2025-12-13)
**Added**: Complete SpectralFit application for Raman & PL spectrum analysis

**Technologies**:
- Streamlit (web UI)
- NumPy + SciPy (numerical computing)
- lmfit (Voigt profile fitting)
- Plotly (interactive visualization)
- Pandas (data export)

**Key Modules**:
- `src/models/`: SpectrumFile, SpectrumData, PeakDefinition, FitResult, ProjectState
- `src/processing/`: despiking (modified Z-score), baseline (polynomial/ALS), fitting (Voigt)
- `src/visualization/`: Plotly composite plots (data + fit + components + residuals)
- `src/io/`: CSV/PNG/HTML export, JSON project save/load
- `src/ui/`: Streamlit tabs (sidebar, preprocess_tab, fit_tab, export_tab)

**Algorithms**:
- Modified Z-score de-spiking (MAD-based, threshold 3-15, default 6)
- Polynomial baseline (degree 1-10)
- Asymmetric Least Squares (ALS) baseline (λ=1e3-1e6, p=0.001-0.1)
- Voigt profile fitting (lmfit VoigtModel, Levenberg-Marquardt)
- Auto-bounds: Raman ±5 cm⁻¹, PL ±30 nm

**Data Model**:
- Session-based state (no database)
- JSON project persistence (versioned schema 1.0.0)
- Multi-file support (1-100 files per session, independent state)

<!-- MANUAL ADDITIONS START -->
<!-- Add project-specific conventions, custom utilities, or workflow notes here -->
<!-- MANUAL ADDITIONS END -->
