"""
Persisted "last used datalog folder" for the Datalog page.

A small JSON sidecar (separate from data/materials.json, whose schema/tests
this deliberately doesn't touch) so the page opens on the folder the operator
was last looking at instead of asking for it again every restart. The tool's
datalogs live several levels down a share; picking that folder is a dozen
clicks, and a page that costs a dozen clicks before it shows anything is a page
that gets opened once.

**This is nexanalyzer's own preference file and is not one of the shared
sidecars.** `tag_store` and `threshold_store` write into the *operator's data
folder*, in a format datalog_monitor also reads and which therefore cannot
change. This one is per-installation, lives in this repo's ``data/``, is
gitignored, and answers to nobody: it carries a `schema_version` only so a
future reader can tell generations apart.

Malformed or missing reads return None rather than raising: losing a remembered
folder must never be the reason a page refuses to open.
"""

import json
from pathlib import Path
from typing import Optional, Union

from core.paths import DATA_DIR

SCHEMA_VERSION = 1


def get_datalog_config_path() -> Path:
    """Absolute path to this installation's datalog.json."""
    return DATA_DIR / "datalog.json"


def load_last_folder(path: Optional[Union[str, Path]] = None) -> Optional[str]:
    """
    Load the remembered datalog folder.

    Returns None if the file doesn't exist, declares a schema this build
    doesn't read, or is malformed (never raises). The folder is **not** checked
    for existence here — a share that has not reconnected yet is still the
    folder the operator wants, and `scanner.discover_csv_files` already returns
    an empty list for an unreachable root, which the page reports as "no runs
    found" rather than as a lost setting.
    """
    path = Path(path) if path is not None else get_datalog_config_path()
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema_version") != SCHEMA_VERSION:
            return None
        folder = data.get("last_folder")
        return folder if isinstance(folder, str) and folder else None
    # UnicodeDecodeError is a ValueError, not an OSError, so a datalog.json
    # whose bytes are not UTF-8 -- half-written, or mangled by a sync client --
    # cleared the other three and raised out of a function documented never to
    # raise, taking the whole page down over a remembered folder. Matches
    # `runcard.io.config_store.load_runcard_folder`, which is this file's twin.
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, AttributeError):
        return None


def save_last_folder(folder: str, path: Optional[Union[str, Path]] = None) -> None:
    """Persist `folder` as the remembered datalog folder."""
    path = Path(path) if path is not None else get_datalog_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": SCHEMA_VERSION, "last_folder": folder}, f, indent=2)
        f.write("\n")
