# SpectralFit

A desktop web application for analyzing Raman and Photoluminescence spectroscopy data.

## Features

- **Data Ingestion**: Load two-column .txt spectrum files (X, Y)
- **Pre-Processing**:
  - Cosmic-ray spike removal (modified Z-score algorithm)
  - Baseline correction (polynomial and Asymmetric Least Squares)
- **Peak Fitting**: Multi-peak Voigt profile fitting with constrained nonlinear optimization
- **Visualization**: Publication-quality interactive plots with styling controls
- **Batch Processing**: Load and process multiple files independently
- **Project Persistence**: Save/load full project state to JSON

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

```bash
# Clone repository
git clone <repo-url>
cd SpectralFit

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

### Workflow

1. **Select Mode**: Choose Raman or PL mode in the sidebar
2. **Load Data**: Upload one or more .txt files (two-column format: X, Y)
3. **Pre-process** (tab 1):
   - Remove cosmic-ray spikes with modified Z-score
   - Apply polynomial or ALS baseline correction
4. **Fit Peaks** (tab 2):
   - Add peak definitions to table (center, amplitude, width)
   - Run Voigt profile fitting
   - View fit results and quality metrics
5. **Export** (tab 3):
   - Customize plot styling
   - Export figures (PNG, HTML)
   - Export fit results (CSV)
6. **Save Project**: Save full session state to JSON for later reload

## File Format

Input files must be two-column .txt files:
- Column 1: Wavenumber (cm⁻¹) for Raman, or Wavelength (nm) for PL
- Column 2: Intensity (raw detector units)
- Delimiter: Tab or comma
- No header row
- Example:
  ```
  100.0   1523.5
  100.5   1520.3
  101.0   1518.9
  ...
  ```

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Generate coverage report
pytest --cov=src --cov-report=html
```

## Development

### Code Style

- Formatter: Black (line length 100)
- Linter: Ruff
- Type Hints: Required for all public functions
- Docstrings: NumPy-style

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Project Structure

```
SpectralFit/
├── app.py                    # Streamlit entry point
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── src/
│   ├── models/               # Data models
│   ├── processing/           # Algorithms (despiking, baseline, fitting)
│   ├── visualization/        # Plotly plotting
│   ├── io/                   # Export and project I/O
│   └── ui/                   # Streamlit UI components
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/             # Sample spectra
```

## License

[Add license information]

## Contributing

[Add contributing guidelines]

## Contact

[Add contact information]
