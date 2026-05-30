@echo off
title SpectralFit Launcher
echo ============================================
echo   SpectralFit - Spectrum Analysis Tool
echo ============================================
echo.

:: Anchor to this script's folder so paths are stable regardless of how it's launched
cd /d "%~dp0"

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: ============================================
:: Auto-update: pull the latest version from GitHub (never blocks launch)
:: ============================================
echo Checking for updates...

:: Is Git available?
git --version >nul 2>&1
if errorlevel 1 (
    echo [SKIP] Git not found - cannot auto-update. Launching current version.
    echo        Install Git from https://git-scm.com/downloads to enable updates.
    echo.
    goto :after_update
)

:: Is this a real git checkout? The .git lives at the repo root (one level up
:: from this SpectralFit folder), since the repo contains SpectralFit/ as a subfolder.
if not exist "..\.git" (
    echo [SKIP] Not a git checkout - cannot auto-update. Launching current version.
    echo        Tip: 'git clone' the repo instead of using a ZIP to get auto-updates.
    echo.
    goto :after_update
)

:: Pull from the repo root. Fast-forward only: if local work has diverged, fail
:: cleanly and keep the current version rather than creating a merge commit.
pushd ".."
git pull --ff-only
set "PULL_RESULT=%errorlevel%"
popd

if not "%PULL_RESULT%"=="0" (
    echo [WARN] Could not update ^(continuing with current version^).
) else (
    echo Up to date with the latest version.
)
echo.

:after_update

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
    echo.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install/update dependencies (runs every launch, so any pulled requirement
:: changes are picked up automatically)
echo Checking dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies are up to date.
echo.

:: Launch the app
echo Starting SpectralFit...
echo The app will open in your browser at http://localhost:8501
echo Press Ctrl+C in this window to stop the server.
echo.
streamlit run app.py
