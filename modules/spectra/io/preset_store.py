"""
JSON-backed storage for material presets.

Presets live in data/materials.json (committed, shared by everyone who
clones the repo) and are edited through the Material Presets page.

The store has two on-disk shapes, and the discriminator is the JSON *type*
rather than any key inside it:

- **v1** is a bare array of flat entries, each carrying its own
  `material_name` and `mode`, keyed in memory by the pair.
- **v2** is an object with `schema_version` and `materials`, each entry keyed
  by material name alone and holding nested `raman` / `pl` / `optical` blocks.

Type-sniffing is what keeps that check honest: a key-sniffing discriminator
has to guess about a half-migrated file, and `migrate_legacy` would rather
raise than guess.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from core.paths import DATA_DIR

from ..models.preset import MaterialPreset

PresetKey = str  # material_name

SCHEMA_VERSION = 2

#: v1 fields that identified the material rather than the measurement, and so
#: belong to the v2 material rather than to either of its technique blocks.
_MATERIAL_FIELDS = ("material_name", "enabled", "description")

#: v1 `mode` value -> the v2 block it becomes.
_MODE_TO_BLOCK = {"Raman": "raman", "PL": "pl"}


def get_presets_path() -> Path:
    """Absolute path to the shared materials.json store."""
    return DATA_DIR / "materials.json"


def migrate_legacy(entries: List[dict]) -> Tuple[List[dict], List[str]]:
    """
    Turn a v1 entry array into v2 material entries. Pure: dicts in, dicts out.

    No disk, no models, no app state, so the one test that matters -- "the
    migration that actually ran lost nothing" -- can compare its output against
    the committed file directly.

    Merge rules, and why:

    - `enabled` is **OR**-ed across the entries being merged. AND would let a
      disabled PL entry switch off a working Raman one, which is a data loss
      dressed up as a setting.
    - `description` joins the distinct non-empty values, Raman first, so
      neither half's wording is silently dropped.
    - A duplicate `(material_name, mode)` keeps the **last**, which is what v1's
      own loader did -- migration is not the place to change who wins.

    Returns
    -------
    (entries, warnings)
        `entries` in v2 shape; `warnings` names every merge that needed a rule
        above, so a surprising result is traceable rather than mysterious.

    Raises
    ------
    ValueError
        On anything that would require guessing: an entry carrying both shapes,
        a half-migrated file where one material appears in both halves, or an
        entry with no usable `material_name`.
    """
    warnings: List[str] = []
    order: List[str] = []
    by_name: Dict[str, dict] = {}
    seen_modes: Dict[str, Dict[str, int]] = {}
    already_v2: Dict[str, bool] = {}
    # name -> block -> description, so the join below can order by technique
    # rather than by however the entries happened to sit in the file.
    descriptions: Dict[str, Dict[str, str]] = {}

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {index} is {type(entry).__name__}, expected an object")

        name = entry.get("material_name")
        if not name:
            raise ValueError(f"Entry {index} has no material_name")

        is_v2 = any(key in entry for key in ("raman", "pl", "optical"))
        is_v1 = "mode" in entry

        if is_v1 and is_v2:
            raise ValueError(
                f"Entry {index} ('{name}') carries both shapes: it has 'mode' and "
                f"also nested blocks. Migrating it would mean guessing which "
                f"settings are current; fix the file by hand."
            )

        if name in already_v2 and already_v2[name] != is_v2:
            raise ValueError(
                f"'{name}' appears in both the old and the new shape. This file "
                f"is half migrated; finish it by hand rather than letting one "
                f"half overwrite the other."
            )
        already_v2[name] = is_v2

        if is_v2:
            if name in by_name:
                raise ValueError(
                    f"Duplicate material '{name}' in the new shape. The old shape "
                    f"allowed one entry per technique; the new one allows one per "
                    f"material, so this needs merging by hand."
                )
            by_name[name] = dict(entry)
            order.append(name)
            continue

        mode = entry.get("mode")
        block_name = _MODE_TO_BLOCK.get(mode)
        if block_name is None:
            raise ValueError(
                f"Entry {index} ('{name}') has mode {mode!r}; expected one of "
                f"{sorted(_MODE_TO_BLOCK)}"
            )

        block = {k: v for k, v in entry.items()
                 if k not in _MATERIAL_FIELDS and k != "mode"}

        if name not in by_name:
            by_name[name] = {
                "material_name": name,
                "enabled": bool(entry.get("enabled", True)),
                "description": "",
            }
            order.append(name)
            seen_modes[name] = {}

        material = by_name[name]

        if block_name in material:
            warnings.append(
                f"'{name}' had more than one {mode} entry "
                f"(entries {seen_modes[name][block_name]} and {index}); kept the last."
            )
        seen_modes[name][block_name] = index
        material[block_name] = block

        # OR, not AND: one disabled technique must not disable the material.
        was_enabled = material["enabled"]
        material["enabled"] = was_enabled or bool(entry.get("enabled", True))
        if material["enabled"] != was_enabled:
            warnings.append(
                f"'{name}' is enabled because its {mode} entry was, though an "
                f"earlier entry was not."
            )

        description = (entry.get("description") or "").strip()
        if description:
            descriptions.setdefault(name, {})[block_name] = description

    # Join descriptions Raman-first, and only distinct ones. Done here rather
    # than as entries arrive because file order is not technique order: the
    # shipped v1 store lists WSe2's PL entry before its Raman one.
    for name, by_block in descriptions.items():
        distinct: List[str] = []
        for block_name in _MODE_TO_BLOCK.values():
            text = by_block.get(block_name)
            if text and text not in distinct:
                distinct.append(text)
        by_name[name]["description"] = " / ".join(distinct)
        if len(distinct) > 1:
            warnings.append(
                f"'{name}' joined {len(distinct)} descriptions: "
                f"{by_name[name]['description']!r}"
            )

    return [by_name[name] for name in order], warnings


def load_presets(
    path: Optional[Union[str, Path]] = None,
) -> Dict[PresetKey, MaterialPreset]:
    """
    Load all material presets from disk, migrating a v1 store on the way in.

    The committed store is already v2, so this shim exists only for a local
    uncommitted edit that predates the change. `load_store` is the same read
    with the migration outcome attached.

    Parameters
    ----------
    path : str or Path, optional
        Store to read. Defaults to get_presets_path() (the app's bundled
        store); overridable for tests.

    Returns
    -------
    dict
        Presets keyed by material_name. Empty dict if the store doesn't exist
        yet (e.g. a fresh checkout before any preset is added).
    """
    return load_store(path).presets


class LoadedStore:
    """A loaded store, plus whether reading it required migrating anything.

    `migrated` is what tells the Material Presets page to offer a re-save, and
    what the "the shipped file is already v2" test asserts is False.
    """

    __slots__ = ("presets", "migrated", "warnings")

    def __init__(self, presets: Dict[PresetKey, MaterialPreset],
                 migrated: bool, warnings: List[str]):
        self.presets = presets
        self.migrated = migrated
        self.warnings = warnings


def load_store(path: Optional[Union[str, Path]] = None) -> LoadedStore:
    """Read the store, migrating a v1 file in memory, and report which happened."""
    path = Path(path) if path is not None else get_presets_path()
    if not path.exists():
        return LoadedStore({}, migrated=False, warnings=[])

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # The JSON type is the discriminator: v1 is an array, v2 an object.
    if isinstance(data, list):
        entries, warnings = migrate_legacy(data)
        migrated = True
    elif isinstance(data, dict):
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"{path} declares schema_version {version!r}; this build reads "
                f"{SCHEMA_VERSION}. A newer store cannot be read by an older app."
            )
        entries = data.get("materials", [])
        warnings = []
        migrated = False
    else:
        raise ValueError(
            f"{path} holds {type(data).__name__}; expected an array (v1) or an "
            f"object (v2)."
        )

    presets: Dict[PresetKey, MaterialPreset] = {}
    for entry in entries:
        preset = MaterialPreset.from_dict(entry)
        presets[preset.material_name] = preset
    return LoadedStore(presets, migrated=migrated, warnings=warnings)


def save_presets(
    presets: Dict[PresetKey, MaterialPreset],
    path: Optional[Union[str, Path]] = None,
) -> None:
    """Write all material presets to disk, sorted by key for clean diffs."""
    path = Path(path) if path is not None else get_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    document = {
        "schema_version": SCHEMA_VERSION,
        "materials": [presets[key].to_dict() for key in sorted(presets.keys())],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2)
        f.write("\n")
