"""The wafer-ID prefix → material table, and the check built on it.

A wafer ID is ``[tool 2][version 2][sequence 2]`` — ``HADH51`` is tool ``HA``,
version ``DH``, wafer 51. The material is a property of the *tool*, so the
table is keyed on the first two letters and holds one entry per tool line.

**Why a convention table and not a record.** There is no per-wafer material
record anywhere: not in the Data Collection share, not on the Drive, not in
this repo. Three separate searches found material asserted only at container
level — a sheet named ``WSe2_SEP Control Table``, a toolkit named
``wse2_optical_analysis``, a generated deck titled ``HADH06 | Material: WSe2``
— never as a field with a value per wafer. Those three conventions can
silently disagree with each other; this table replaces all of them with one
that is version-controlled and reviewable.

**Two files, and only one of them is shared.** ``data/material_prefixes.json``
is committed and is the team's agreed table. ``material_prefixes.local.json``
sits beside it, is gitignored, and holds whatever an operator added from the
app. The local file is layered *over* the committed one, and every lookup says
which of the two answered.

That split is the whole point of the overlay. A single committed file the app
could write would let one operator add ``QU`` → MoS2 on their machine and
another add ``QU`` → WS2 on theirs, with both seeing a green "verified" and
neither seeing the other. Since a locally-resolved answer is marked as such all
the way to the OneNote page, a local guess can never present itself as the
team's agreed answer. It mirrors the split this repo already draws between
``data/materials.json`` (committed, shared) and ``data/report_settings.json``
(gitignored, per-installation).

The check is a guardrail, not broad validation: five of the six tool lines grow
WSe2, so it passes for almost every wafer. What it earns its place for is the
``QU`` wafer left on the previous sample's WSe2 preset, and the tool line
nobody has added yet.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from core.paths import DATA_DIR

#: How many leading characters of a wafer ID name the tool line. Positions 3-4
#: are a version, which has never carried a material change — so the key stops
#: at two. A version that *did* change chemistry would need a four-letter entry
#: taking precedence over its tool's, which is a change to this constant and to
#: `resolve`, not to the file format.
PREFIX_LEN = 2

#: Verdicts from `check_material`. Kept distinct because "we did not check" and
#: "we checked and it disagrees" must never render alike.
MATCH = "match"
MISMATCH = "mismatch"
UNKNOWN_PREFIX = "unknown_prefix"
NO_SELECTION = "no_selection"

#: Where a resolved material came from. Carried through to the page so a
#: locally-added prefix is visibly not the team's agreed answer.
SOURCE_SHARED = "shared"
SOURCE_LOCAL = "local"


def get_prefix_table_path() -> Path:
    """Absolute path to the committed, shared prefix table."""
    return DATA_DIR / "material_prefixes.json"


def get_local_prefix_table_path() -> Path:
    """Absolute path to this installation's gitignored overlay."""
    return DATA_DIR / "material_prefixes.local.json"


def _read_prefixes(path: Path) -> dict[str, str]:
    """Read one table file's prefix map, or {} if absent or malformed.

    Never raises: a hand-edited file with a trailing comma must degrade to
    "this prefix is unknown", which the page already handles, rather than
    taking down the upload page on import.
    """
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    prefixes = data.get("prefixes") if isinstance(data, dict) else None
    if not isinstance(prefixes, dict):
        return {}

    return {
        str(key).upper(): value
        for key, value in prefixes.items()
        if isinstance(value, str) and value
    }


def load_prefixes(
    shared_path: Optional[Union[str, Path]] = None,
    local_path: Optional[Union[str, Path]] = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(shared, local)`` prefix maps, each uppercased.

    They are returned apart rather than merged because the caller needs to
    know which file answered; `resolve` is what layers them.
    """
    shared = _read_prefixes(
        Path(shared_path) if shared_path is not None else get_prefix_table_path()
    )
    local = _read_prefixes(
        Path(local_path) if local_path is not None else get_local_prefix_table_path()
    )
    return shared, local


#: A wafer ID is two letters of tool line, two of version, two digits of
#: sequence — HADH51, VBBE12, QUAB07. Used only to warn: a name that does not
#: match still publishes, because this app does not own the naming convention
#: and a folder the operator can see is not something to refuse.
WAFER_ID_RE = re.compile(r"^[A-Z]{4}\d{2}$")


def looks_like_wafer_id(wafer_id: str) -> bool:
    """Whether a name has the shape of a wafer ID.

    `HA` is a tool prefix, not a wafer — it resolves against the table
    perfectly well and would otherwise report a confident green match for a
    page named after a whole tool line. The check exists so that a partial
    entry says so rather than passing silently.
    """
    return bool(WAFER_ID_RE.match((wafer_id or "").strip().upper()))


def wafer_prefix(wafer_id: str) -> str:
    """The tool-line prefix of a wafer ID, uppercased.

    Short or empty IDs pass through as whatever they are: a folder named ``X``
    yields ``X``, which will miss the table and report as unknown. That is the
    correct outcome — it is not a wafer ID — and it beats raising on a folder
    name the operator can see and fix.
    """
    return (wafer_id or "").strip().upper()[:PREFIX_LEN]


@dataclass(frozen=True)
class PrefixResolution:
    """One prefix lookup: what answered, and which file said so."""

    prefix: str
    material: Optional[str]
    source: Optional[str]  # SOURCE_SHARED, SOURCE_LOCAL, or None if unknown

    @property
    def is_local(self) -> bool:
        """True when only the gitignored overlay knew this prefix."""
        return self.source == SOURCE_LOCAL


def resolve(
    wafer_id: str,
    shared: Optional[dict[str, str]] = None,
    local: Optional[dict[str, str]] = None,
) -> PrefixResolution:
    """Look a wafer ID's material up, local overlay taking precedence.

    Local wins so that an operator who has added a prefix sees their own
    answer rather than a stale shared one — but the resolution says it came
    from the overlay, and every surface that renders it says so too.
    """
    if shared is None or local is None:
        loaded_shared, loaded_local = load_prefixes()
        shared = loaded_shared if shared is None else shared
        local = loaded_local if local is None else local

    prefix = wafer_prefix(wafer_id)

    if prefix in local:
        return PrefixResolution(prefix, local[prefix], SOURCE_LOCAL)
    if prefix in shared:
        return PrefixResolution(prefix, shared[prefix], SOURCE_SHARED)
    return PrefixResolution(prefix, None, None)


@dataclass(frozen=True)
class MaterialCheck:
    """The verdict shown in the app and written onto the OneNote page."""

    verdict: str
    wafer_id: str
    selected: Optional[str]
    expected: Optional[str]
    resolution: PrefixResolution

    @property
    def is_local(self) -> bool:
        """True when the expected material came from the local overlay."""
        return self.resolution.is_local

    def summary(self) -> str:
        """One line, for the page and the app. Same words in both places.

        The operator can fix a mis-selection in seconds if told and cannot if
        not, so the warning is shown at upload time as well as written onto
        the page where the team sees it.
        """
        if self.verdict == NO_SELECTION:
            return f"No material selected for {self.wafer_id}."

        if self.verdict == UNKNOWN_PREFIX:
            return (
                f"Material not verified: prefix {self.resolution.prefix!r} is not in "
                f"the table. Operator selected {self.selected}."
            )

        suffix = " (locally added, not yet shared)" if self.is_local else ""

        if self.verdict == MISMATCH:
            return (
                f"Material mismatch: selected {self.selected}, "
                f"prefix table says {self.expected}{suffix}."
            )

        return f"Material {self.selected} matches the prefix table{suffix}."


def check_material(
    wafer_id: str,
    selected_material: Optional[str],
    shared: Optional[dict[str, str]] = None,
    local: Optional[dict[str, str]] = None,
) -> MaterialCheck:
    """Compare the operator's selected material against the prefix table.

    Never blocks and never raises — every outcome is a verdict the caller
    renders and then uploads anyway. A check that stopped an upload would
    assume the table is always right, and the table is a convention someone
    maintains by hand: the day a tool changes chemistry it is confidently
    wrong for every wafer on that line, and a blocking check would then be
    worked around rather than corrected.
    """
    resolution = resolve(wafer_id, shared=shared, local=local)
    selected = (selected_material or "").strip() or None

    if selected is None:
        verdict = NO_SELECTION
    elif resolution.material is None:
        verdict = UNKNOWN_PREFIX
    elif _normalise(resolution.material) == _normalise(selected):
        verdict = MATCH
    else:
        verdict = MISMATCH

    return MaterialCheck(
        verdict=verdict,
        wafer_id=(wafer_id or "").strip(),
        selected=selected,
        expected=resolution.material,
        resolution=resolution,
    )


def _normalise(material: str) -> str:
    """Fold a material name for comparison.

    The table says ``WSe2`` and a preset may be named ``WSe2`` or ``wse2``;
    those are the same material and must not read as a mismatch. Nothing
    fancier than case and surrounding space — ``WSe2`` and ``WSe₂`` are left
    to differ, because collapsing unicode subscripts here would hide a real
    naming inconsistency that belongs in the preset list instead.
    """
    return material.strip().casefold()


def add_local_prefix(
    prefix: str,
    material: str,
    path: Optional[Union[str, Path]] = None,
) -> None:
    """Add one prefix to the gitignored overlay, creating it if needed.

    Deliberately writes the *local* file and never the committed one. The app
    offering a one-click "add this prefix" is a convenience; letting that
    convenience edit the shared table would put an uncommitted entry on one
    machine that every other machine disagrees with, while both show a green
    verdict. The entry is marked as local wherever it is rendered, so it reads
    as provisional until someone promotes it into the committed table.
    """
    path = Path(path) if path is not None else get_local_prefix_table_path()
    existing = _read_prefixes(path)
    existing[wafer_prefix(prefix)] = material.strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "prefixes": existing}, f, indent=2)
        f.write("\n")
