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

# Move to script directory
cd "$(dirname "$0")"

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

# Install/update dependencies
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
