# SpectralFit User Guide

A step-by-step guide for installing and running SpectralFit on **Windows** and **macOS**.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Step 1: Install Python](#step-1-install-python)
3. [Step 2: Download SpectralFit](#step-2-download-spectralfit)
4. [Step 3: Run SpectralFit](#step-3-run-spectralfit)
5. [Step 4: Create a Desktop Shortcut (Optional)](#step-4-create-a-desktop-shortcut-optional)
6. [Using SpectralFit](#using-spectralfit)
7. [File Format](#file-format)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

- **OS**: Windows 10/11 or macOS 12+
- **Python**: 3.10 or higher
- **Disk space**: ~500 MB (including Python and dependencies)
- **Browser**: Any modern browser (Chrome, Edge, Firefox, Safari)

---

## Step 1: Install Python

### Windows

1. Go to **https://www.python.org/downloads/**
2. Click **"Download Python 3.x.x"** (the latest version)
3. Run the installer
4. **IMPORTANT**: Check the box **"Add Python to PATH"** at the bottom of the installer
5. Click **"Install Now"**
6. Verify: Open **Command Prompt** (search "cmd" in Start menu) and type:
   ```
   python --version
   ```
   You should see something like `Python 3.12.x`.

### macOS

**Option A — Official installer:**
1. Go to **https://www.python.org/downloads/**
2. Download the macOS installer
3. Run the `.pkg` file and follow the prompts

**Option B — Homebrew (if you have Homebrew installed):**
```bash
brew install python3
```

**Verify**: Open **Terminal** and type:
```bash
python3 --version
```
You should see something like `Python 3.12.x`.

---

## Step 2: Download SpectralFit

Get the SpectralFit folder from your team (shared drive, USB, or zip file). The folder should contain:

```
SpectralFit/
├── app.py
├── start.bat          ← Windows launcher
├── start.sh           ← Mac/Linux launcher
├── requirements.txt
├── src/
├── presets/
└── ...
```

Place it anywhere convenient, for example:
- Windows: `C:\Users\YourName\SpectralFit`
- Mac: `~/SpectralFit`

---

## Step 3: Run SpectralFit

### Windows

1. Open the `SpectralFit` folder in File Explorer
2. **Double-click `start.bat`**
3. A terminal window will appear. On first run it will:
   - Create a virtual environment (`venv` folder)
   - Install all required packages
   - This may take 1-2 minutes on first run
4. Your browser will automatically open to **http://localhost:8501**
5. To stop the app, press `Ctrl+C` in the terminal window, or simply close it

### macOS

1. Open **Terminal**
2. Navigate to the SpectralFit folder:
   ```bash
   cd ~/SpectralFit
   ```
3. Make the script executable (first time only):
   ```bash
   chmod +x start.sh
   ```
4. Run:
   ```bash
   ./start.sh
   ```
5. On first run it will create a virtual environment and install packages
6. Your browser will open to **http://localhost:8501**
7. To stop the app, press `Ctrl+C` in the terminal

---

## Step 4: Create a Desktop Shortcut (Optional)

### Windows

1. Right-click `start.bat` → **Create shortcut**
2. Drag the shortcut to your Desktop
3. (Optional) Right-click the shortcut → **Properties** → **Change Icon** to customize

### macOS

1. Open **Automator** (search in Spotlight)
2. Choose **Application**
3. Add a **Run Shell Script** action with:
   ```bash
   cd ~/SpectralFit && ./start.sh
   ```
4. Save as `SpectralFit` to your Desktop or Applications folder

**Alternatively**, create a simple alias in Terminal:
```bash
echo 'alias spectralfit="cd ~/SpectralFit && ./start.sh"' >> ~/.zshrc
source ~/.zshrc
```
Then just type `spectralfit` in any terminal to launch.

---

## Quick Start: Auto-Workflow with Material Presets

The fastest way to process spectra is using the **auto-workflow** with a material preset file. This runs the entire pipeline (X-range crop, de-spiking, baseline correction, peak fitting) in a single click.

### 1. Prepare a Preset File

Create an Excel file (`.xlsx`) where **each sheet** defines one material-mode combination.

**Sheet naming convention:** `Material_Mode` (e.g., `WSe2_Raman`, `MoS2_PL`)

**Sheet layout:**

| Row | Content |
|-----|---------|
| Row 1 | Setting headers: `x_min`, `x_max`, `despike_threshold`, `baseline_algo`, `baseline_param`, `exclusion_ranges`, `description` |
| Row 2 | Setting values: e.g., `180`, `400`, `6`, `ALS`, `10000`, `240-270`, `Low-freq Raman` |
| Row 3 | *(empty — separator)* |
| Row 4 | Peak headers: `label`, `center`, `tolerance` |
| Row 5+ | Peak data: e.g., `E2g`, `249`, `5` |

An example preset file is included at `presets/material_presets.xlsx`.

### 2. Load the Preset File

1. Open the **sidebar** (click the `>` arrow at the top-left)
2. Under **Material Presets**, click **"Browse Preset File"**
3. Select your `.xlsx` file — the presets will load automatically
4. If the file updates, click **"Reload"** to refresh

### 3. Load Your Spectrum Files

1. In the sidebar under **Load Spectra**, click **"Browse File Folder"**
2. Select the folder containing your `.txt` spectrum files
3. All `.txt` files in the folder will be loaded automatically
4. The mode (Raman/PL) is auto-detected from filename patterns (e.g., `RM*` → Raman, `PL*` → PL)

### 4. Select a Material

1. In the sidebar under **Material Presets**, use the **material dropdown** to select the target material
2. Only materials matching the current mode (Raman or PL) are shown
3. A summary of the preset settings (baseline algorithm, peak count, notes) appears below

### 5. Run the Workflow

**Single file:**
- Click **"Run Auto-Workflow"** to process the currently selected spectrum
- The pipeline executes: X-range crop → De-spike → Baseline correction → Peak fitting
- Results appear in the plot and fit results table below it

**All files (batch):**
- If multiple files are loaded, a **"Run All Files"** button appears
- Click it to process every loaded file using the selected preset
- A progress bar shows the batch status
- After completion, a summary shows how many files succeeded

### 6. Review and Export

- Use the **file navigation arrows** (above the plot) to browse through processed files
- Check the **fit results table** below each plot for peak parameters and R² values
- Go to the **Export** section in the control panel to save results as CSV, PNG, or HTML

---

## Using SpectralFit (Manual Workflow)

SpectralFit is a browser-based tool for Raman and Photoluminescence spectrum analysis. The manual workflow follows these steps:

### 1. Load Data
- Click the **sidebar** (left edge) to expand it
- Or use **"Browse Folder"** to load an entire folder of spectra

### 2. Select a Spectrum
- Use the **file dropdown** or **left/right arrows** at the top of the plot to switch between loaded files

### 3. Set Processing Range
- In the right control panel, expand **"Processing Range"**
- Set the X-axis range to crop your spectrum to the region of interest

### 4. De-spiking (Remove Cosmic Rays)
- Expand **"De-spiking"**
- Adjust the threshold and preview the result in real time
- Click **"Apply"** when satisfied

### 5. Baseline Correction
- Expand **"Baseline"**
- Choose an algorithm (Polynomial, ALS, Rolling Ball, Spline, or airPLS)
- Adjust parameters and preview the baseline overlay
- Click **"Apply"** to subtract

### 6. Peak Fitting
- Expand **"Peak Fitting"**
- Use **"Auto Find Peaks"** for automatic detection, or manually add peaks
- Click **"Fit"** to perform Voigt profile fitting
- Review the fit quality (R² value) and individual peak parameters

### 7. Export Results
- Expand **"Export"**
- Save plots as PNG/SVG, fit parameters as CSV, or the full project as JSON

---

## File Format

SpectralFit accepts **two-column .txt files**:

```
120.5	1523.2
121.0	1540.8
121.5	1535.1
...
```

- **Column 1**: Wavenumber (cm⁻¹) or Wavelength (nm)
- **Column 2**: Intensity
- **Delimiter**: Tab or comma
- **No header row**

---

## Troubleshooting

### "Python is not installed or not in PATH"
- **Windows**: Reinstall Python and make sure to check **"Add Python to PATH"**. Then restart your terminal.
- **Mac**: Make sure `python3 --version` works in Terminal. If not, reinstall from python.org.

### "pip install fails" or network errors
- Check your internet connection — packages are downloaded from the internet on first run
- If behind a corporate proxy, ask your IT team for proxy settings
- Try running manually:
  ```
  pip install -r requirements.txt
  ```

### The browser doesn't open automatically
- Manually open your browser and go to **http://localhost:8501**

### "Address already in use" error
- Another instance of SpectralFit (or another Streamlit app) is already running
- Close the other terminal window, or run on a different port:
  ```
  streamlit run app.py --server.port 8502
  ```

### App is slow or unresponsive
- Large files or many loaded spectra can use significant memory
- Try loading fewer files at once
- Close other browser tabs to free memory

### Updating SpectralFit
When you receive a new version:
1. Replace the files in your SpectralFit folder (keep the `venv` folder)
2. Run `start.bat` / `start.sh` — it will automatically install any new dependencies
