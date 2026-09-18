"""
Remembering how each sheet was last plotted.

A small JSON sidecar in ``data/``, gitignored and per-installation, following
`core.io.report_settings`'s pattern — including its rule that a malformed or
absent file is never an error. Losing a remembered plot config is an
inconvenience; a page that refuses to open because its preferences file has a
stray comma is not.

Keyed by **sheet name**, not by file path. One plot draws from one tool and one
tool is one sheet, so switching from ``HA_SplitTable`` to ``QUAD_SplitTable``
is switching experiments and deserves its own remembered axes; those two sheets
share only 10 of 74 column names, so a single global config would blank itself
on every switch. Path is deliberately *not* part of the key: the same workbook
exists in several folders across OneDrive, and keying by path would mean
reconfiguring whenever a different copy was opened, which is precisely the
friction this exists to remove.

A remembered column that the sheet no longer has is dropped on load rather
than restored, because `viz.scatter.build_scatter` raises on a column it can't
find and a stale preference must not be able to break the page.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Union

from core.paths import DATA_DIR

#: Schema marker. Nothing migrates it yet -- an unreadable or unknown document
#: is discarded and rebuilt, which is the right trade for a preferences file.
SCHEMA_VERSION = 1


def get_config_path() -> Path:
    """Absolute path to this installation's plot_explorer.json."""
    return DATA_DIR / "plot_explorer.json"


def load_document(path: Optional[Union[str, Path]] = None) -> Dict:
    """The whole settings document, or an empty one. Never raises."""
    path = Path(path) if path is not None else get_config_path()
    empty: Dict = {"schema_version": SCHEMA_VERSION, "sheets": {}, "last_path": None, "last_sheet": None}

    if not path.exists():
        return empty

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return empty

    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        return empty
    if not isinstance(data.get("sheets"), dict):
        data["sheets"] = {}
    return data


def save_document(document: Dict, path: Optional[Union[str, Path]] = None) -> None:
    """Write the settings document, silently doing nothing if it can't.

    A read-only ``data/`` -- an installation on a locked-down share, say --
    must cost the user their remembered settings, not their session.
    """
    path = Path(path) if path is not None else get_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(document, f, indent=2)
    except OSError:
        pass


def load_sheet_state(sheet: str, path: Optional[Union[str, Path]] = None) -> Optional[Dict]:
    """What was last set for ``sheet``, or None if nothing was."""
    state = load_document(path).get("sheets", {}).get(sheet)
    return state if isinstance(state, dict) else None


def save_sheet_state(sheet: str, state: Dict, path: Optional[Union[str, Path]] = None) -> None:
    """Remember ``state`` for ``sheet``, leaving every other sheet's alone."""
    document = load_document(path)
    document["sheets"][sheet] = state
    save_document(document, path)


def load_last_location(path: Optional[Union[str, Path]] = None) -> Dict[str, Optional[str]]:
    """The workbook and sheet last opened, so a restart resumes where it left off."""
    document = load_document(path)
    return {"path": document.get("last_path"), "sheet": document.get("last_sheet")}


def save_last_location(
    workbook: Optional[str], sheet: Optional[str], path: Optional[Union[str, Path]] = None
) -> None:
    """Remember which workbook and sheet were open."""
    document = load_document(path)
    document["last_path"] = workbook
    document["last_sheet"] = sheet
    save_document(document, path)


def prune_to_columns(config: Dict, columns) -> Dict:
    """``config`` with every reference to an absent column removed.

    The quiet fallback the design calls for: a config remembered against a
    sheet that has since lost a column comes back with that control unset
    rather than raising. Scalar column references are blanked; ``hover_data``
    keeps whichever of its columns survive.
    """
    available = {str(c) for c in columns}
    pruned = dict(config)

    for key in ("x", "y", "color", "symbol", "size", "hover_name",
                "facet_row", "facet_col", "error_x", "error_y"):
        if pruned.get(key) and pruned[key] not in available:
            pruned[key] = None

    hover = pruned.get("hover_data")
    if isinstance(hover, list):
        pruned["hover_data"] = [c for c in hover if c in available]

    return pruned
