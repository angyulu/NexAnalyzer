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

## Using SpectralFit

SpectralFit is a browser-based tool for Raman and Photoluminescence spectrum analysis. The workflow follows these steps:

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
