"""
What a datalog run says about the tool: per-channel statistics, where a
process value left its setpoint's tolerance band, and when the run settled at
its final commanded temperature.

Pure pandas. No Streamlit, no disk — which is the point of the one unusual
signature here: `compute_all_violations` takes the tolerance *resolver* as a
parameter (defaulting to `get_tolerance_pct` below) instead of importing the
threshold sidecar, so every number in this file can be checked against a
hand-built frame and `lambda thresholds, name: 5.0`. The source app inverted
that dependency for the same reason and then kept a second, byte-identical
copy of the resolver in its page; there is one copy here, and the page imports
it.

`TIME_COLUMN` is defined here rather than beside the rest of the CSV's
vocabulary in `io/scanner.py`, and the direction is forced: this package must
import without Streamlit, and the scanner's per-file cache is an
`st.cache_data` decorator. One definition, read by the scanner that produces
the column and by `viz/charts.py` that plots it — the label-based slicing in
`_build_segment` and the parse that makes the column monotonic cannot be
allowed to disagree about its name.
"""

from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

TIME_COLUMN = "Time"
"""The datalog's timestamp column, logged as ``%Y/%m/%d %H:%M:%S``.

Every row that reaches this module has a valid value here: the scanner drops
unparseable timestamps immediately after reading, which is what lets
`_build_segment` subtract two cells without guarding for NaT.
"""

SV_ZERO_EPSILON = 1e-6
"""Below this |SV|, percentage deviation from the setpoint is undefined.

An idle channel logs ``SV = 0.000`` -- on the ground-truth run all eight MFCs
sit at zero for most of the two hours -- and ``(PV - 0) / 0`` is either a
divide-by-zero or, worse, a finite number that reads as a real excursion. Those
rows are reported as NaN rather than 0 or inf, which is what stops the
violations table filling up with "every idle MFC is out of tolerance".
"""


def get_tolerance_pct(thresholds: dict, pair_name: str) -> float:
    """
    The tolerance band, in percent, for one PV/SV pair.

    Two levels and no merging: a per-channel override replaces the global
    default outright. The key is the **pair name** (``"Heater"``, ``"MFC-1"``,
    ``"P1_H"``), never a column name, so renaming a column in the controller's
    log orphans any override saved against the old name.

    Parameters
    ----------
    thresholds : dict
        As returned by `io.threshold_store.load_thresholds`, which always
        supplies ``global_default_pct``. That is why this line indexes it
        directly while reaching for ``overrides`` with ``.get`` — a hand-built
        dict missing the global default is a programming error and should say
        so, whereas a file that predates per-channel overrides is just old.
    pair_name : str
        The PV/SV pair name from `io.scanner.detect_pv_sv_pairs`.
    """
    return thresholds.get("overrides", {}).get(pair_name, thresholds["global_default_pct"])


def compute_summary_stats(df: pd.DataFrame, channels: List[str]) -> pd.DataFrame:
    """
    Min / max / mean per channel, in the order the caller asked for them.

    Two separate skips, and neither produces a row of NaNs: a channel this file
    does not carry is absent, and a channel that carries nothing but NaN has no
    population to summarize. A row of NaNs under a channel heading looks like a
    measurement that read zero; no row at all looks like what it is.

    ``Avg`` is the unweighted mean of the samples, **not** a time-weighted
    average. That is only correct because the controller logs at a steady 1 Hz —
    a run with a gap in its log biases this number toward whatever the tool was
    doing while it was still writing.

    Returns
    -------
    pd.DataFrame
        Columns ``Channel / Min / Max / Avg``. When no channel qualifies this is
        ``pd.DataFrame([])`` — zero rows **and zero columns** — so callers test
        ``.empty`` before reaching for ``["Channel"]``.
    """
    rows = []
    for channel in channels:
        if channel not in df.columns:
            continue
        series = df[channel].dropna()
        if series.empty:
            continue
        # dropna once, up front, so all three statistics describe the same
        # population rather than three differently-sized ones.
        rows.append({
            "Channel": channel,
            "Min": series.min(),
            "Max": series.max(),
            "Avg": series.mean(),
        })
    return pd.DataFrame(rows)


def compute_deviation_pct(df: pd.DataFrame, pv_col: str, sv_col: str) -> pd.Series:
    """
    Signed percentage deviation of the process value from its setpoint.

    ``(PV - SV) / SV * 100``, so positive means the tool is running above what
    it was told to. Signed rather than absolute because an overshoot and an
    undershoot are different faults; the violations table collapses the sign
    away only after the segments are built.

    Rows where ``|SV| <= SV_ZERO_EPSILON`` — an idle channel, or a NaN setpoint,
    which compares False and lands in the same branch — are NaN. Strict
    inequality against the absolute value, so an exact ``0.0`` is excluded and a
    negative setpoint still works.

    The result carries `df`'s index, gaps included. That is load-bearing:
    `_build_segment` slices this series by label.
    """
    pv = df[pv_col]
    sv = df[sv_col]
    deviation = pd.Series(index=df.index, dtype=float)
    valid = sv.abs() > SV_ZERO_EPSILON
    deviation[valid] = (pv[valid] - sv[valid]) / sv[valid] * 100
    deviation[~valid] = float("nan")
    return deviation


def find_violation_mask(deviation_pct: pd.Series, tolerance_pct: float) -> pd.Series:
    """
    True where the deviation is outside a symmetric band.

    Strictly greater than, so a deviation exactly equal to the tolerance is
    *in* tolerance — a channel held at precisely its stated limit is not a
    finding. ``NaN > x`` is False, so every row the epsilon guard blanked is
    automatically non-violating and needs no second test.
    """
    return deviation_pct.abs() > tolerance_pct


def _build_segment(df: pd.DataFrame, pair_name: str, deviation_pct: pd.Series,
                   start_idx, end_idx) -> dict:
    """One row of the violations table, spanning `start_idx` to `end_idx`.

    ``deviation_pct.loc[start:end]`` is label-based and includes both
    endpoints. It is correct only because the index stays monotonically
    increasing after the scanner's dropna — the index has gaps but never
    changes direction. A port that resets or re-sorts the index silently gets
    a different slice here, with no error to show for it.

    ``Max Deviation (%)`` loses the sign: an overshoot and an undershoot of the
    same size report identically. The magnitude is what the table ranks by; the
    direction is readable off the chart, where the deviating samples are marked
    on the PV trace itself.
    """
    seg_slice = deviation_pct.loc[start_idx:end_idx]
    start_time = df.loc[start_idx, TIME_COLUMN]
    end_time = df.loc[end_idx, TIME_COLUMN]
    return {
        "Channel": pair_name,
        "Start": start_time,
        "End": end_time,
        "Duration (s)": (end_time - start_time).total_seconds(),
        "Max Deviation (%)": seg_slice.abs().max(),
    }


def find_violation_segments(df: pd.DataFrame, pair_name: str, mask: pd.Series,
                            deviation_pct: pd.Series) -> List[dict]:
    """
    Collapse a per-sample out-of-tolerance mask into contiguous segments.

    One pass in row order, rising edge to falling edge. A segment ends at the
    **last flagged row**, not at the unflagged row that closed it, so the
    reported window contains only violating samples.

    Two consequences worth stating, because both look like bugs and are not:

    - A single-sample violation reports ``Duration (s) == 0.0``. Duration is
      the span between the first and last violating samples, not sample count
      times the log period, so at 1 Hz a five-sample violation reads 4.0 s.
    - A violation still in progress when the log ends is emitted by the check
      after the loop rather than dropped. The run whose heater never came back
      into band is exactly the one worth reporting.

    `mask` is zipped against `df.index` **positionally**, never aligned by
    label, so it must be the mask derived from this same frame.
    """
    segments = []
    in_violation = False
    seg_start_idx = None
    prev_idx = None
    for idx, flagged in zip(df.index, mask):
        if flagged and not in_violation:
            in_violation = True
            seg_start_idx = idx
        elif not flagged and in_violation:
            in_violation = False
            segments.append(_build_segment(df, pair_name, deviation_pct, seg_start_idx, prev_idx))
        prev_idx = idx
    if in_violation:
        segments.append(_build_segment(df, pair_name, deviation_pct, seg_start_idx, prev_idx))
    return segments


def find_final_plateau_start(df: pd.DataFrame, column: str) -> Optional[pd.Timestamp]:
    """
    First timestamp of the *last* run of rows sitting at the column's max value.

    This is the process t=0 that comparison mode aligns runs on. Runs start at
    arbitrary wall-clock times and spend different amounts of time in load,
    pump-down, purge and ramp, so overlaying them on start time puts each run's
    growth phase at a different x and nothing comparable lines up.

    A setpoint column can sit at its ceiling from row 0 — a static value logged
    before the real ramp begins — so the *first* occurrence of the max is a
    trivial early match. Taking the last upward crossing into the max instead
    finds the genuine "settled at the final setpoint" moment, but only if the
    run's true final setpoint is itself the column's global max. It need not be:
    the row-0 value can be a leftover from whatever ran on the controller
    *before* this run started, rather than anything this run's recipe commands.

    That is not hypothetical. In ``2026-08-06_173312~VBBE00.csv``, ``Heater SV``
    reads **910 for its first 1025 rows** — 17:33:12 to 17:50:22, 17 min 10 s —
    then drops to 106 and ramps back up to **850**, which it holds for the
    remaining 4907 rows. 850 is the runcard's own commanded ramp target and
    every other run's plateau; 910 is the stale leftover, and it is the
    column's global maximum. The real plateau never reaches back up to it, so
    "last rising edge into max" degenerates to matching only the row-0
    artifact and returns the run's start time — the exact degenerate answer
    alignment exists to avoid, and one that looks entirely plausible.

    So the leading block of row 0's value is excluded before the target is
    computed — and excluded **only from the target search**. The rising-edge
    scan still runs over the full, unmodified column, which is what lets the
    stale 910 block still count as "at or above 850" and keeps the scan robust
    to a setpoint that overshoots slightly or is logged with jitter.

    Two residual limits, preserved knowingly: the exclusion only handles a stale
    value that is constant *from row 0* — one appearing a few rows in, or two
    distinct stale plateaus, still defeats it — and a real final setpoint lower
    than some mid-run excursion would lock the target onto the excursion.

    Returns
    -------
    Optional[pd.Timestamp]
        None for an empty column, an all-NaN target, or no rising edge. The
        page falls back to wall-clock start and says out loud which runs fell
        back: a silent fallback looks exactly like a real misalignment.
    """
    series = df[column]
    if series.empty:
        return None
    first_value = series.iloc[0]
    changed = series != first_value
    # .to_numpy() because this indexes an Index with the mask *positionally*.
    # The mask came from this same series, so position is what is meant; saying
    # so explicitly stops a future index change from turning it into a
    # label lookup that quietly returns the wrong row.
    if changed.any():
        search_series = series.loc[series.index[changed.to_numpy()][0]:]
    else:
        search_series = series
    target = search_series.max()
    if pd.isna(target):
        return None
    at_max = series >= target
    # fill_value=False makes row 0 a rising edge whenever it is already at or
    # above target. NaN >= target is False, so a NaN run breaks a plateau and
    # manufactures an extra rising edge where the data resumes.
    rising_edges = at_max & ~at_max.shift(1, fill_value=False)
    if not rising_edges.any():
        return None
    last_edge_idx = series.index[rising_edges.to_numpy()][-1]
    return df.loc[last_edge_idx, TIME_COLUMN]


def compute_all_violations(
    df: pd.DataFrame,
    pv_sv_pairs: List[Tuple[str, str, str]],
    thresholds: dict,
    get_tolerance_pct: Callable[[dict, str], float] = get_tolerance_pct,
) -> Tuple[pd.DataFrame, Dict[str, Tuple[pd.Series, pd.Series]]]:
    """
    Every pair's violations, pooled into one chronological table.

    Parameters
    ----------
    df : pd.DataFrame
        One parsed run.
    pv_sv_pairs : List[Tuple[str, str, str]]
        ``(pair_name, pv_col, sv_col)`` triples. A pair whose columns are not in
        this frame is skipped whole — no mask, no segments — rather than
        contributing an empty channel to the table.
    thresholds : dict
        Passed straight to `get_tolerance_pct`; never read here.
    get_tolerance_pct : Callable
        The resolver, injected so this module stays free of the sidecar. It
        defaults to the one above, which is the only copy — the source app kept
        a duplicate in its page and required the two to be edited together,
        which is not a mechanism.

    Returns
    -------
    (violations_df, masks)
        `masks` maps ``pair_name -> (mask, deviation_pct)`` for **every pair
        processed, including the ones with no violations at all**: the chart
        needs the deviation series to mark a clean channel as clean.
        `violations_df` is sorted by ``Start`` across channels, and its index is
        deliberately not reset — the row labels still point back into the pooled
        list. An empty result is ``pd.DataFrame([])``, zero columns included,
        which is why the sort is guarded: ``sort_values("Start")`` on it raises
        KeyError.
    """
    all_segments = []
    masks: Dict[str, Tuple[pd.Series, pd.Series]] = {}
    for pair_name, pv_col, sv_col in pv_sv_pairs:
        if pv_col not in df.columns or sv_col not in df.columns:
            continue
        tolerance_pct = get_tolerance_pct(thresholds, pair_name)
        deviation_pct = compute_deviation_pct(df, pv_col, sv_col)
        mask = find_violation_mask(deviation_pct, tolerance_pct)
        masks[pair_name] = (mask, deviation_pct)
        all_segments.extend(find_violation_segments(df, pair_name, mask, deviation_pct))

    violations_df = pd.DataFrame(all_segments)
    if not violations_df.empty:
        # Stable, so segments starting in the same second keep pv_sv_pairs order.
        violations_df = violations_df.sort_values("Start")
    return violations_df, masks
