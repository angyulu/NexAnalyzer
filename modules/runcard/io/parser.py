"""
Runcard CSV reading: the command rows a growth run was programmed from.

A runcard is the file handed to the reactor: three unheaded, comma-separated
columns — command name, param A, param B — terminated by an `End,--,--` row and
then padded with several hundred `--,--,--` filler rows out to the tool's fixed
program length. The padding count belongs to the originating tool family and
not to the recipe (981 filler rows on every VBBE* card, 975 on every HAD*), so
nothing here may assume a file length; the `End` sentinel is the only reliable
end of the recipe.

`utf-8-sig`, not `utf-8`: none of the sampled files carries a BOM, but one
would land on the first command's name and turn it into an unrecognised string.
That drops the first command silently instead of raising — the one corruption
this format cannot report.

Two doors, deliberately:

- `parse_runcard` is pure. It takes a path and returns rows, so it is testable
  with a `tmp_path` fixture and nothing else.
- `load_runcard` is the memoized one, keyed on the path **and its mtime**, and
  it is what the app calls. In the app this was ported from, every widget
  interaction re-read and re-parsed all 53 CSVs in the folder; keying on mtime
  means a recipe edited in place still re-reads, which a path-only key would
  not.
"""

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Union

#: A trailing `_runcard` on the filename is a naming habit, not part of the run
#: identifier. Case-insensitive and end-anchored: `NX123_RUNCARD.csv` and
#: `NX123_runcard.csv` name the same run, while a file simply called
#: `runcard.csv` has no leading underscore and keeps its whole name.
_RUNCARD_SUFFIX_RE = re.compile(r"_runcard$", re.IGNORECASE)

#: Streamlit's memoizer, resolved on first use rather than imported at module
#: scope. `core/viz/render.py` defers its own Streamlit import for the same
#: reason: an `io` module that Streamlit has to be importable for is an `io`
#: module a headless test cannot touch, and the layering here keeps Streamlit
#: in `ui/` and in the `viz` modules that render.
_CACHED_PARSE = None


@dataclass(frozen=True)
class RuncardCommand:
    """One surviving row of a runcard.

    `index` counts **surviving commands**, not CSV lines: skipped padding does
    not consume an index, so the number is stable against a tool that pads
    differently. Nothing in this app reads it — it is carried because a row's
    position in the program is the only way to name it when reporting a
    malformed recipe back to an operator.

    `params` holds every column after the first, so a well-formed runcard row
    yields two. It is not fixed at two: a datalog export fed to this parser by
    mistake produces a 37-element tuple, and that shape difference is the
    cheapest tell that the file is not a recipe.
    """

    index: int
    name: str
    params: Tuple[str, ...]


def parse_runcard(path: Union[str, Path]) -> List[RuncardCommand]:
    """
    Read `path` and return its command rows, `End` included and last.

    Every cell is stripped before any test. A row is skipped when it has fewer
    than three cells (blank trailing lines, which `csv` yields as `[]`) or when
    its first cell is `--` or empty — which is precisely the padding filter.
    Nothing else is validated: params stay strings and are never coerced here,
    because what `params[0]` means depends on the command — a unit for `Wait`,
    a channel name for `MFC/PC`, a temperature for `Heater Ramp` — and a parser
    that guessed would have to guess wrong for one of them.

    The `End` sentinel is **kept** and parsing stops on it. The CLI this was
    ported from dropped it and scanned to EOF instead; keeping it means the
    returned list is the program as written, and stopping means the ~975 filler
    rows after it are never touched.

    Raises
    ------
    OSError
        Missing, locked, or cloud-only file.
    UnicodeDecodeError, csv.Error
        Not a text CSV at all. Both propagate: a caller walking a folder has to
        decide whether one unreadable file costs it the whole listing, and this
        function cannot make that call for it. `list_runcards` makes it one way.
    """
    commands: List[RuncardCommand] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            row = [c.strip() for c in row]
            if len(row) < 3 or row[0] in ("--", ""):
                continue
            commands.append(RuncardCommand(index=len(commands), name=row[0], params=tuple(row[1:])))
            if row[0] == "End":
                break
    return commands


def load_runcard(path: Union[str, Path]) -> List[RuncardCommand]:
    """`parse_runcard`, memoized on the file's path and modification time.

    The app calls this; tests call `parse_runcard`. Splitting them is what lets
    the parse be exercised with no Streamlit cache in the way, and lets the
    cache key be computed out here, where the filesystem is allowed to be
    touched twice — once to stat, once to read.

    A file that cannot be stat'ed is given mtime `-1.0` rather than being
    rejected here, so it still reaches `parse_runcard` and still raises the
    `OSError` that says what is actually wrong with it.
    """
    global _CACHED_PARSE
    if _CACHED_PARSE is None:
        import streamlit as st

        # max_entries bounds a folder walk: one runcard parses to at most a few
        # hundred small frozen dataclasses, so 512 of them is a few MB, while
        # the default is unbounded. show_spinner=False because the default
        # renders "Running _parse_at_mtime(...)" once per file, in the middle of
        # the page's own progress bar.
        _CACHED_PARSE = st.cache_data(show_spinner=False, max_entries=512)(_parse_at_mtime)
    return _CACHED_PARSE(str(path), file_mtime(path))


def _parse_at_mtime(path: str, mtime: float) -> List[RuncardCommand]:
    """`parse_runcard(path)` under a cache key that also carries `mtime`.

    `mtime` is deliberately unused in the body: it exists only to move the
    cache key when the file behind an unchanged path changes. Editing a recipe
    in place is the normal way these files change, and a path-only key would
    serve the pre-edit program for the life of the process.
    """
    return parse_runcard(path)


def file_mtime(path: Union[str, Path]) -> float:
    """Modification time, or -1.0 for a file that cannot be stat'ed.

    Public because it is two answers, not one: it moves `load_runcard`'s cache
    key, and it is also the only date these recipes carry — the clock inside
    them starts at zero, so "when was this written" can only be asked of the
    file. The Runcard page shows it as a column.
    """
    try:
        return os.path.getmtime(path)
    except OSError:
        return -1.0


def list_runcards(folder: Union[str, Path]) -> List[str]:
    """
    Every CSV under `folder` (recursively) that reads as a real recipe.

    Three gates, in order: the file must read; it must yield at least one
    command; and its reconstructed clock must advance. The third gate is the
    one doing the work — a real recipe always holds somewhere, so a
    `total_time` of zero means nothing in the file matched a command this app
    knows. It is what separates recipes from the tool's own datalog exports,
    which sit in the same folders and parse *loudly*: 6904 "commands", the
    first named `Time` and the rest named after their own timestamps, none of
    which advances the clock. On the example folder that is 40 accepted and 13
    rejected, and the 13 rejected are exactly the datalogs.

    Returns `str` paths, sorted, because that is what the page stores in
    session state and what keys the per-file caches.

    A non-directory — a missing path, or a file — returns `[]` rather than
    raising: "there is nothing here" is the honest answer for a folder that
    went away, and a page that refuses to open is not.

    Every per-file failure is swallowed, which is a deliberate widening of the
    ported behaviour. There, only `OSError` and `UnicodeDecodeError` were
    caught, so a single `Heater Ramp,abc,--` anywhere in the tree raised
    `ValueError` out of the validity gate and cost the operator the entire
    listing. One bad file must cost one row.
    """
    from ..processing import growth_window

    # Deferred, and it must stay deferred: `growth_window` imports
    # `RuncardCommand` from this module at its own module scope, so hoisting
    # this to the top makes the two a cycle that fails on whichever is imported
    # first.

    root = Path(folder)
    if not root.is_dir():
        return []

    runcards: List[str] = []
    for path in sorted(root.rglob("*.csv")):
        try:
            commands = load_runcard(path)
            if not commands:
                continue
            if growth_window.build_timeline(commands).total_time <= 0:
                continue
        except (OSError, UnicodeDecodeError, csv.Error, ValueError, IndexError):
            continue
        runcards.append(str(path))
    return runcards


def derive_run_id(path: Union[str, Path]) -> str:
    """
    The run identifier a filename is carrying, upper-cased.

    Operators prefix an export date onto the stem and suffix the word runcard
    onto it, and neither is part of the run: `0810_NX123_runcard.csv` and
    `NX123.csv` name the same run and must display identically, or one recipe
    appears in a folder listing twice under two names.

    Only a **leading, all-digit** segment is dropped, and only one: the stem is
    split on every `_`, and the first segment goes if `str.isdigit()` accepts
    it. So `20240810_a_b.csv` becomes `A_B`, `NX123_runcard.csv` becomes
    `NX123`, and `runcard.csv` becomes `RUNCARD` — with no underscore there is
    no leading segment to drop, and `_runcard$` does not match a bare
    `runcard`.
    """
    run_id = Path(path).stem
    if "_" in run_id:
        parts = run_id.split("_")
        if parts[0].isdigit():
            run_id = "_".join(parts[1:])
    return _RUNCARD_SUFFIX_RE.sub("", run_id).upper()
