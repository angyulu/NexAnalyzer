"""
Persisted "last used runcard folder" for the Runcard page.

A small JSON sidecar (separate from data/materials.json, whose schema and tests
this deliberately doesn't touch) so the page opens on the folder it was last
pointed at instead of on an empty picker. Recipes live in one deep archive
folder that nobody wants to navigate to twice a day, and the native folder
dialog has no history of its own.

Per-installation, so it's gitignored — and deliberately **not** the sidecar
this folder shares with the tool that writes it. `runcard_tags.json` and
`thresholds.json` live with the data and are read by both apps; this file is
nexanalyzer's own preference and belongs to this machine.

Malformed or missing reads return `None` rather than raising: this is a
convenience, and losing a remembered folder must never be the reason a page
refuses to open.

It carries `schema_version` even though nothing reads a second generation yet.
`core/io/report_settings.py` does not, and the cost of that is that a future
reader of *its* file cannot tell an old shape from a new one without guessing
at the keys.
"""

import json
from pathlib import Path
from typing import Optional, Union

from core.paths import DATA_DIR

SCHEMA_VERSION = 1


def get_runcard_config_path() -> Path:
    """Absolute path to this installation's runcard.json.

    Named `_config_` rather than `get_runcard_path`, which in a module tree
    whose subject is runcard *files* would read as "the path of a runcard".
    """
    return DATA_DIR / "runcard.json"


def load_runcard_folder(path: Optional[Union[str, Path]] = None) -> Optional[str]:
    """
    Load the persisted runcard folder.

    Returns None if the file doesn't exist, declares a schema this build
    doesn't read, or is malformed (never raises). Existence of the folder is
    deliberately not checked here: an archive on a disconnected network share
    is still the right answer to "where was I", and the page can say so far
    more usefully than a `None` can.
    """
    path = Path(path) if path is not None else get_runcard_config_path()
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema_version") != SCHEMA_VERSION:
            return None
        folder = data.get("folder")
        return folder if isinstance(folder, str) and folder else None
    # UnicodeDecodeError is a ValueError, not an OSError, so a sidecar whose
    # bytes are not UTF-8 -- a half-written or sync-mangled file -- cleared the
    # other three and raised out of a function documented never to raise,
    # making a lost preference the reason the page would not open. That is the
    # one thing this module exists to prevent.
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, AttributeError):
        return None


def save_runcard_folder(folder: str, path: Optional[Union[str, Path]] = None) -> None:
    """Persist `folder` as the runcard folder to open next time."""
    path = Path(path) if path is not None else get_runcard_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": SCHEMA_VERSION, "folder": folder}, f, indent=2)
        f.write("\n")
