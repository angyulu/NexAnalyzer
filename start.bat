@echo off
title NexAnalyzer Launcher
echo ============================================
echo   NexAnalyzer - Nexstrom Data Analyzer
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

:: Is this a real git checkout? This script sits at the repo root, next to .git.
if not exist ".git" (
    echo [SKIP] Not a git checkout - cannot auto-update. Launching current version.
    echo        Tip: 'git clone' the repo instead of using a ZIP to get auto-updates.
    echo.
    goto :after_update
)

:: Fast-forward only: if local work has diverged, fail cleanly and keep the
:: current version rather than creating a merge commit.
git pull --ff-only
if errorlevel 1 goto :update_failed
echo Up to date with the latest version.
echo.
goto :after_update

:update_failed
:: Separate the two real causes. The common one is local edits to tracked files:
:: editing material presets in-app rewrites data\materials.json, which is
:: committed and shared, so git refuses to overwrite it. Reported as a generic
:: warning, that silently pins the user to an old version forever.
git diff --quiet HEAD
if errorlevel 1 goto :update_blocked
echo [WARN] Could not update - offline, or no access to the repo.
echo        Continuing with the current version.
echo.
goto :after_update

:update_blocked
echo [WARN] Update BLOCKED by your local changes to these tracked files:
git --no-pager diff --name-only HEAD
echo.
echo        You will keep launching an OLD version until this is resolved.
echo        Set the changes aside and relaunch:  git stash
echo        To get them back afterwards:         git stash pop
echo        See USER_GUIDE.md ^(Troubleshooting^) for details.
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
echo Starting NexAnalyzer...
echo The app will open in your browser at http://localhost:8501
echo Press Ctrl+C in this window to stop the server.
echo.
streamlit run app.py
