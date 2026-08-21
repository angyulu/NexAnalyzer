"""
Persisted "default material" setting for the Sample Report page.

A small JSON sidecar (separate from data/materials.json, whose schema/tests
this deliberately doesn't touch) so the Material dropdown can remember the
last-used material across app restarts. Per-installation, so it's gitignored.
"""

import json
from pathlib import Path
from typing import Optional, Union

from ..paths import DATA_DIR


def get_report_settings_path() -> Path:
    """Absolute path to this installation's report_settings.json."""
    return DATA_DIR / "report_settings.json"


def load_default_material(path: Optional[Union[str, Path]] = None) -> Optional[str]:
    """
    Load the persisted default material name.

    Returns None if the file doesn't exist or is malformed (never raises).
    """
    path = Path(path) if path is not None else get_report_settings_path()
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        material = data.get("default_material")
        return material if isinstance(material, str) and material else None
    except (json.JSONDecodeError, OSError):
        return None


def save_default_material(material_name: str, path: Optional[Union[str, Path]] = None) -> None:
    """Persist `material_name` as the default material."""
    path = Path(path) if path is not None else get_report_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"default_material": material_name}, f, indent=2)
        f.write("\n")
