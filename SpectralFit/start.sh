#!/bin/bash
echo "============================================"
echo "  SpectralFit - Spectrum Analysis Tool"
echo "============================================"
echo

# Check Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Please install Python 3.10+ from https://www.python.org/downloads/"
    echo "Or on Mac: brew install python3"
    exit 1
fi

# Move to script directory (anchor paths regardless of how it's launched)
cd "$(dirname "$0")"

# ============================================
# Auto-update: pull the latest version from GitHub (never blocks launch)
# ============================================
echo "Checking for updates..."

if ! command -v git &> /dev/null; then
    echo "[SKIP] Git not found - cannot auto-update. Launching current version."
    echo "       Install Git from https://git-scm.com/downloads to enable updates."
    echo
elif [ ! -d "../.git" ]; then
    # The .git lives at the repo root (one level up), since the repo contains
    # SpectralFit/ as a subfolder.
    echo "[SKIP] Not a git checkout - cannot auto-update. Launching current version."
    echo "       Tip: 'git clone' the repo instead of using a ZIP to get auto-updates."
    echo
else
    # Pull from the repo root. Fast-forward only: if local work has diverged, fail
    # cleanly and keep the current version rather than creating a merge commit.
    if ( cd .. && git pull --ff-only ); then
        echo "Up to date with the latest version."
    else
        echo "[WARN] Could not update (continuing with current version)."
    fi
    echo
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created."
    echo
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies (runs every launch, so any pulled requirement
# changes are picked up automatically)
echo "Checking dependencies..."
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi
echo "Dependencies are up to date."
echo

# Launch the app
echo "Starting SpectralFit..."
echo "The app will open in your browser at http://localhost:8501"
echo "Press Ctrl+C to stop the server."
echo
streamlit run app.py
