"""
JSON-backed storage for material presets.

Presets live in data/materials.json (committed, shared by everyone who
clones the repo) and are edited through the Material Presets page.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from core.paths import DATA_DIR

from ..models.preset import MaterialPreset

PresetKey = Tuple[str, str]  # (material_name, mode)


def get_presets_path() -> Path:
    """Absolute path to the shared materials.json store."""
    return DATA_DIR / "materials.json"


def load_presets(path: Optional[Union[str, Path]] = None) -> Dict[PresetKey, MaterialPreset]:
    """
    Load all material presets from disk.

    Parameters
    ----------
    path : str or Path, optional
        Store to read. Defaults to get_presets_path() (the app's bundled
        store); overridable for tests.

    Returns
    -------
    dict
        Presets keyed by (material_name, mode). Empty dict if the store
        doesn't exist yet (e.g. a fresh checkout before any preset is added).
    """
    path = Path(path) if path is not None else get_presets_path()
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    presets = {}
    for entry in data:
        preset = MaterialPreset.from_dict(entry)
        presets[(preset.material_name, preset.mode)] = preset
    return presets


def save_presets(presets: Dict[PresetKey, MaterialPreset], path: Optional[Union[str, Path]] = None) -> None:
    """Write all material presets to disk, sorted by key for clean diffs."""
    path = Path(path) if path is not None else get_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered = [presets[key].to_dict() for key in sorted(presets.keys())]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2)
        f.write("\n")
