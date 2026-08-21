"""
Filesystem locations the app reads and writes.

Anchored on this file rather than the working directory, so the paths hold
however the app is launched (Streamlit from the repo root, pytest from
anywhere, a double-clicked start.bat).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Runtime data: shared material presets (committed) and per-installation
# preferences (gitignored). Kept out of the package tree so it's obvious
# what's app data and what's code.
DATA_DIR = PROJECT_ROOT / "data"
