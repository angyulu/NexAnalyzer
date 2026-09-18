"""
A worksheet, turned into something plottable.

Everything here is a pure function over a path or a DataFrame — no Streamlit —
because this is where the bugs live and unit tests are the only cheap way to
find them.

Four problems this solves, all of them found in a real workbook
(``Milestone and Schedule.xlsx``, sheet ``HA_SplitTable``, 602 rows) rather
than imagined:

**Two header rows.** Row 1 names the column, row 2 qualifies it — usually a
unit (``torr``, ``sccm``, degrees C), sometimes not (``E2g`` under ``FWHM``,
``relative intensity`` under ``LA/E2g``). Read with one header row, every
numeric column begins with the string ``"torr"`` and comes back as text. Read
with both and joined, the columns name themselves: ``H2O (torr)``,
``FWHM (E2g)``.

**Repeated names.** That sheet has three columns called ``H2O`` and two called
``O2``. pandas would mangle them to ``H2O.1``/``H2O.2``, which is unreadable
in a dropdown. The qualifier row separates most of them; whatever still
collides gets an explicit ``#2`` suffix rather than a silent one.

**Mixed types in a numeric column.** 19 of that sheet's 38 columns hold numbers
*and* prose — ``90(1000Torr)``, ``1->4(0.2sccm)``, ``12min30s``,
``35.5-37.5``. Plotly reads such a column as categorical and draws a
plausible-looking chart with a nonsense axis. `coerce_column` offers three
readings of those strings and reports what each one costs; the page shows a
preview before any of it is applied. None of them is the default, because
``1->4`` means the flow was *ramped*, and deciding it "is" 1 is an
interpretation of an experiment, not a parse.

**Filler rows.** 14% of that sheet is entirely blank, and one sibling sheet is
99% blank — a pre-formatted template. Blank rows are dropped on load (an empty
row is not a data point); nothing else is, and the sheet picker shows populated
row counts so an empty sheet announces itself instead of looking like a broken
plot.
"""

import re
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

import pandas as pd

#: Strings a human writes to mean "not applicable". Treated as missing when a
#: column is coerced to numbers -- but NOT when deciding whether a row is
#: blank, because a row of slashes can still carry a wafer ID, and dropping it
#: would be discarding a record rather than skipping a gap.
NULL_MARKERS = frozenset({"/", "na", "n/a", "-", "--", "none", "nan"})

#: A signed number, refusing to start immediately after a digit or a dot. The
#: lookbehind is what makes "35.5-37.5" two numbers rather than 35.5 and
#: -37.5: the minus there is a range separator, and reading it as a sign would
#: turn a 36.5 midpoint into -1.0.
_NUMBER = re.compile(r"(?<![\d.])[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

#: How `coerce_column` may read a string that isn't already a number.
COERCION_STRATEGIES: Tuple[str, ...] = ("none", "strict", "leading", "midpoint")

#: Labels for the strategy dropdown, keyed by strategy.
COERCION_LABELS: Dict[str, str] = {
    "none": "Leave as-is",
    "strict": "Strict - non-numbers become blank",
    "leading": "Leading number - '12min30s' becomes 12",
    "midpoint": "Range midpoint - '35.5-37.5' becomes 36.5",
}


class SheetInfo(NamedTuple):
    """One worksheet as the picker needs to describe it.

    ``populated_rows`` counts rows below the first one that have any content at
    all, so a template sheet reads as "5 rows" instead of looking like a
    plotting bug.
    """

    name: str
    populated_rows: int
    columns: int


class ColumnProfile(NamedTuple):
    """What a column contains, for choosing axes and coercion strategies.

    ``kind`` is one of ``numeric``, ``text``, ``mixed``, ``datetime`` or
    ``empty``. ``mixed`` is the one that matters: it is exactly the state in
    which Plotly will silently draw a categorical axis.
    """

    name: str
    kind: str
    filled: int
    distinct: int
    numeric: int
    text: int
    examples: Tuple[str, ...]


class CoercionResult(NamedTuple):
    """A coerced column and what the coercion cost.

    ``lost`` is the number of cells that held something before and hold
    nothing after -- the count the page must show, because a scatter that
    quietly dropped 65 of 430 runs is a different plot than the one you asked
    for.
    """

    values: pd.Series
    lost: int


def _is_blank(value) -> bool:
    """True for a cell holding nothing a person typed."""
    if value is None:
        return True
    try:
        if isinstance(value, float) and pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and not value.strip()


def list_sheets(path: str, header_rows: int = 1) -> List[SheetInfo]:
    """Every worksheet in ``path``, with its populated row count.

    ``header_rows`` is passed through so the count matches what `read_sheet`
    will actually load. Without it a two-header sheet advertises one more row
    than it yields, and an off-by-one between the picker and the plot is the
    kind of discrepancy that costs an afternoon to explain.

    Uses openpyxl's read-only mode rather than pandas: this runs to build a
    dropdown, and parsing every sheet into a DataFrame to count its rows would
    make opening a 17-sheet workbook feel broken.
    """
    from openpyxl import load_workbook

    skip = max(header_rows, 1)
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        infos = []
        for name in wb.sheetnames:
            ws = wb[name]
            populated = 0
            columns = 0
            for index, row in enumerate(ws.iter_rows(values_only=True)):
                width = sum(1 for cell in row if not _is_blank(cell))
                columns = max(columns, len(row))
                if index >= skip and width:
                    populated += 1
            infos.append(SheetInfo(name=name, populated_rows=populated, columns=columns))
        return infos
    finally:
        wb.close()


def build_labels(header_rows: Sequence[Sequence]) -> List[Optional[str]]:
    """Column labels from one or more header rows.

    ``None`` marks a column to drop: one whose header cells are all empty,
    which in a hand-kept sheet is a spacer rather than a variable.

    Multiple rows are joined as ``name (qualifier)`` -- the form the columns
    are already referred to in conversation ("H2O (torr)"), and the only thing
    that separates three columns all called ``H2O``. Anything that still
    collides is suffixed ``#2``, ``#3``: an explicit marker of a genuine
    duplicate, rather than pandas' ``.1`` which reads like part of the name.
    """
    if not header_rows:
        return []

    width = max(len(row) for row in header_rows)
    labels: List[Optional[str]] = []

    for column in range(width):
        parts = []
        for row in header_rows:
            cell = row[column] if column < len(row) else None
            if not _is_blank(cell):
                parts.append(str(cell).strip())

        if not parts:
            labels.append(None)
        elif len(parts) == 1:
            labels.append(parts[0])
        else:
            labels.append("{} ({})".format(parts[0], " ".join(parts[1:])))

    return _suffix_duplicates(labels)


def _suffix_duplicates(labels: Sequence[Optional[str]]) -> List[Optional[str]]:
    """Make repeated labels unique, leaving the first occurrence untouched."""
    seen: Dict[str, int] = {}
    out: List[Optional[str]] = []
    for label in labels:
        if label is None:
            out.append(None)
            continue
        count = seen.get(label, 0) + 1
        seen[label] = count
        out.append(label if count == 1 else "{} #{}".format(label, count))
    return out


def read_sheet(path: str, sheet: str, header_rows: int = 1) -> pd.DataFrame:
    """One worksheet as a DataFrame: labels joined, spacers and blanks dropped.

    ``header_rows`` is a setting rather than a guess. Sniffing it would get the
    messy sheets -- the only ones that need it -- wrong, and wrong silently.

    Raises
    ------
    ValueError
        If ``header_rows`` exceeds the sheet's height, which is a real answer
        to "did I point this at the right rows?" and better than an empty plot.
    """
    if header_rows < 1:
        raise ValueError("header_rows must be at least 1")

    raw = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")

    if len(raw) < header_rows:
        raise ValueError(
            "Sheet {!r} has {} row(s); {} header row(s) were requested.".format(sheet, len(raw), header_rows)
        )

    header = [list(raw.iloc[i]) for i in range(header_rows)]
    labels = build_labels(header)

    body = raw.iloc[header_rows:].reset_index(drop=True)
    keep = [i for i, label in enumerate(labels) if label is not None]
    body = body.iloc[:, keep]
    body.columns = [labels[i] for i in keep]

    body = drop_blank_rows(body)
    # Excel hands back a column of floats as object dtype whenever the header
    # rows sat above it; without this every numeric column would profile as
    # text and every axis would be categorical.
    return body.infer_objects()


def drop_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with content, in order.

    Blank means *every* cell empty. A row holding only ``/`` survives: the
    slashes say "not applicable", which is a statement about the run, and the
    row usually still names a wafer.
    """
    if df.empty:
        return df
    mask = df.apply(lambda row: not all(_is_blank(v) for v in row), axis=1)
    return df[mask].reset_index(drop=True)


def _classify(value) -> str:
    """``numeric``, ``datetime``, ``null`` or ``text`` for a single cell."""
    if _is_blank(value):
        return "null"
    if isinstance(value, bool):
        return "text"
    if isinstance(value, (int, float)):
        return "numeric"
    if hasattr(value, "year") and hasattr(value, "month"):
        return "datetime"
    if str(value).strip().lower() in NULL_MARKERS:
        return "null"
    return "text"


def profile_columns(df: pd.DataFrame) -> List[ColumnProfile]:
    """What each column holds, for the column table on the page.

    The ``examples`` are non-numeric values only -- when a column profiles as
    ``mixed``, the useful question is "what are the 65 things that aren't
    numbers?", and showing three of them is what makes the coercion strategies
    a choice rather than a guess.
    """
    profiles = []
    for name in df.columns:
        series = df[name]
        kinds = [_classify(v) for v in series]
        numeric = kinds.count("numeric")
        text = kinds.count("text")
        stamps = kinds.count("datetime")
        filled = numeric + text + stamps

        if not filled:
            kind = "empty"
        elif stamps and not numeric and not text:
            kind = "datetime"
        elif numeric and text:
            kind = "mixed"
        elif numeric:
            kind = "numeric"
        else:
            kind = "text"

        examples: List[str] = []
        for value, classification in zip(series, kinds):
            if len(examples) == 3:
                break
            if classification == "text":
                shown = str(value).strip()
                if shown not in examples:
                    examples.append(shown)

        profiles.append(
            ColumnProfile(
                name=str(name),
                kind=kind,
                filled=filled,
                distinct=int(series.nunique(dropna=True)),
                numeric=numeric,
                text=text,
                examples=tuple(examples),
            )
        )
    return profiles


def _numbers_in(text: str) -> List[float]:
    """Every number in a string, range separators respected."""
    return [float(m.group()) for m in _NUMBER.finditer(text)]


def _coerce_value(value, strategy: str) -> Optional[float]:
    """One cell under one strategy, or None where it yields no number."""
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if text.lower() in NULL_MARKERS:
        return None

    if strategy == "strict":
        try:
            return float(text)
        except ValueError:
            return None

    numbers = _numbers_in(text)
    if not numbers:
        return None
    if strategy == "leading":
        return numbers[0]
    if strategy == "midpoint":
        # The first two numbers, because "1->4(0.2sccm)" states a ramp and
        # then an unrelated aside; averaging all three would invent a value
        # that appears nowhere in the run.
        return numbers[0] if len(numbers) == 1 else (numbers[0] + numbers[1]) / 2.0
    raise ValueError("Unknown coercion strategy: {!r}".format(strategy))


def coerce_column(series: pd.Series, strategy: str) -> CoercionResult:
    """``series`` read as numbers, with the count of what that cost.

    ``strategy="none"`` returns the column untouched and a cost of zero, so a
    caller can apply the configured strategy for every column without
    special-casing the default.
    """
    if strategy not in COERCION_STRATEGIES:
        raise ValueError("Unknown coercion strategy: {!r}".format(strategy))
    if strategy == "none":
        return CoercionResult(values=series, lost=0)

    coerced = pd.Series(
        [_coerce_value(v, strategy) for v in series], index=series.index, dtype="float64"
    )
    had = sum(1 for v in series if _classify(v) in ("numeric", "text", "datetime"))
    lost = had - int(coerced.notna().sum())
    return CoercionResult(values=coerced, lost=max(lost, 0))


def coercion_preview(series: pd.Series, strategy: str, limit: int = 5) -> List[Tuple[str, str]]:
    """``(before, after)`` pairs for the values a strategy actually changes.

    Only non-numeric cells are shown: a column of 365 numbers and 65 strings
    needs a preview of the 65, and filling the table with "890 -> 890.0" would
    hide them.
    """
    pairs: List[Tuple[str, str]] = []
    for value in series:
        if _classify(value) != "text":
            continue
        result = _coerce_value(value, strategy)
        pairs.append((str(value).strip(), "(blank)" if result is None else "{:g}".format(result)))
        if len(pairs) == limit:
            break
    return pairs


def apply_coercions(
    df: pd.DataFrame, strategies: Dict[str, str]
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """``df`` with each named column coerced; also what each coercion cost.

    Columns absent from ``strategies``, and columns named there but missing
    from ``df``, are both left alone -- the second case is a remembered config
    meeting a different sheet, which must not be an error.
    """
    out = df.copy()
    losses: Dict[str, int] = {}
    for name, strategy in strategies.items():
        if name not in out.columns or strategy == "none":
            continue
        result = coerce_column(out[name], strategy)
        out[name] = result.values
        if result.lost:
            losses[name] = result.lost
    return out, losses


class RowFilter(NamedTuple):
    """One column narrowed: to a set of values, or to a numeric range.

    Rows whose value in ``column`` is empty are excluded either way. That is a
    real decision rather than an oversight: a filter says "these runs", and a
    run with no value for the thing being filtered on isn't known to be one of
    them.
    """

    column: str
    keep: Optional[Tuple[str, ...]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None


def apply_filters(df: pd.DataFrame, filters: Sequence[RowFilter]) -> pd.DataFrame:
    """``df`` narrowed by every filter in turn.

    A filter naming a column the sheet doesn't have is skipped, so a config
    remembered against another sheet degrades to "no filter" instead of
    raising.
    """
    out = df
    for row_filter in filters:
        if row_filter.column not in out.columns:
            continue
        series = out[row_filter.column]

        if row_filter.keep is not None:
            wanted = set(row_filter.keep)
            mask = series.map(lambda v: not _is_blank(v) and str(v).strip() in wanted)
            out = out[mask]
            continue

        if row_filter.minimum is None and row_filter.maximum is None:
            continue
        numbers = pd.to_numeric(series, errors="coerce")
        mask = numbers.notna()
        if row_filter.minimum is not None:
            mask &= numbers >= row_filter.minimum
        if row_filter.maximum is not None:
            mask &= numbers <= row_filter.maximum
        out = out[mask]

    return out.reset_index(drop=True)


def distinct_values(series: pd.Series, limit: int = 500) -> List[str]:
    """Sorted distinct non-empty values, as strings, for a filter's multiselect.

    Capped: a multiselect listing 500 wafer IDs is already unusable, and
    building one for 50,000 would hang the page rather than help.
    """
    values = {str(v).strip() for v in series if not _is_blank(v)}
    return sorted(values)[:limit]
