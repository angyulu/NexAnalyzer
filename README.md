# NexAnalyzer v3.2.2

Nexstrom's measurement data analyzer. A desktop web app that turns raw measurement files into
fitted results and shareable reports, driven by per-material presets rather than manual
parameter tuning.

**Modules available today:** Raman & photoluminescence spectra (peak fitting + sample reports).
The platform is built so further techniques plug in alongside it — see
[Architecture](#architecture).

---

## Quick start

### Windows: one click

Download **[Install-NexAnalyzer.bat](https://raw.githubusercontent.com/angyulu/NexAnalyzer/main/Install-NexAnalyzer.bat)** (right-click the link, *Save link as...*) and
double-click it. It installs Python and Git if they are missing, downloads the app, puts a
shortcut on your Desktop, and launches it — nothing else to do. Your browser may warn about
keeping a `.bat` file; choose **Keep**.

### Any platform: clone it yourself

**Prerequisites:** Python 3.10+ (tick "Add Python to PATH" on Windows) and
[Git](https://git-scm.com/downloads).

```bash
git clone https://github.com/angyulu/NexAnalyzer.git nexanalyzer
cd nexanalyzer
```

- **Windows**: double-click `start.bat`
- **macOS / Linux**: `./start.sh`

The launcher pulls the latest version, sets up a virtual environment, installs dependencies,
and opens the app at `http://localhost:8501`. It auto-updates on every run, and never blocks:
if you're offline or Git is missing, it launches the version you already have.

> Downloading a ZIP works too, but ZIP copies have no Git history, so they **won't
> auto-update** — clone with Git.

<details>
<summary>Manual setup</summary>

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```
</details>

---

## Features

### Raman & PL spectra

- **Material presets** drive the whole pipeline in one click: X-range crop → cosmic-ray spike
  removal (modified Z-score) → baseline correction (Polynomial, ALS, Rolling Ball, Spline,
  airPLS, or None) → multi-peak Voigt fitting. Peak positions and processing parameters are
  defined per material and edited in-app on the **Material Presets** page.
- **Batch processing**: run the same preset across every loaded file ("Run All Files").
- **Interactive plots** with auto-managed layers — after a run the plot shows the fit result,
  with raw and intermediate layers available under View Options.
- **Export**: PNG/HTML figures, per-file fit parameters, and a master CSV across all fitted files.

### Sample reports

- **One-click PPTX** from a sample folder's 9-point OM + Raman + PL measurement grid: pick the
  folder, pick a material, click Generate. Out comes a three-slide report — OM grid with
  fit-summary tables, then a 3×3 grid of each Raman point's fitted spectrum, then the same for PL.
- **On-screen preview** of the real generated slides, saved alongside the `.pptx` as
  `_page1.png` / `_page2.png` / `_page3.png`.

> Report previews drive Microsoft PowerPoint via COM automation, so they require Windows with
> Office installed. Without it you still get the `.pptx` — only the preview images are skipped.

---

## Architecture

```
app.py                 Composition root: page config, module session state, routing
pages/                 One file per screen (Spectra, Sample Report, Material Presets)
core/                  Platform — knows nothing about peaks or spectra
  io/                  Native dialogs, figure rasterization, output filenames
  report/              PPTX assembly, slide rasterization, report row contracts
  viz/                 Page-width-aware figure rendering
  paths.py             Where app data lives
  version.py           Single source of truth for name + version
modules/               One package per measurement technique
  spectra/             Raman & PL: models, processing, UI, figures
data/                  materials.json (shared, committed) + local preferences
tests/                 unit/ + integration/
docs/                  Architecture and algorithm notes
```

**The dependency rule:** `modules/*` may import `core`; `core` never imports `modules`.
Within a tree, imports are relative; across trees, absolute. Adding a technique means adding a
package under `modules/` and registering its pages in `app.py` — nothing in `core` changes.

---

## Usage

1. **Load data** — **Browse Spectrum Files** in the sidebar, pick one or more `.txt` files.
2. **Configure a material** (first time only) — on **Material Presets**, add a material with its
   processing settings and peak templates.
3. **Select the material** on the **Spectra** page sidebar dropdown.
4. **Run** — **🚀 Run Auto-Workflow** (one file) or **🚀 Run All Files** (batch).
5. **Export** — Quick Export (PNG/HTML/CSV) or Batch Export (master CSV).

### Input file format

Two-column (or multi-Y) `.txt` files, no header:

- Column 1: Wavenumber (cm⁻¹) or wavelength (nm)
- Column 2+: Intensity — one column for standard files, several for multi-Y acquisitions
- Delimiter: tab, comma, or whitespace (auto-detected)

---

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** — step-by-step usage
- **[CHANGELOG.md](CHANGELOG.md)** — version history
- **[docs/Summary.md](docs/Summary.md)** — architecture, data model, design decisions
- **[docs/Baseline_Algo.md](docs/Baseline_Algo.md)** — baseline correction theory and analysis
- **[docs/Fitting_Algo.md](docs/Fitting_Algo.md)** — peak fitting theory and implementation history

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 136 tests
python -m ruff check .
```

## License

Proprietary — © Nexstrom. Internal use only; see [LICENSE](LICENSE).

## Contact

angyu.lu@nexstrom.com
