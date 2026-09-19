"""
The recipe clock: a list of runcard commands replayed into a timeline, a
reconstructed temperature trace, and the growth window cut out of it.

Pure arithmetic — no Streamlit, no file access. It takes the `RuncardCommand`
rows `io.parser` produced and gives back what every surface on the Runcard page
reads.

**Exactly two commands advance the clock: `Wait` and `Check Status`.**
Everything else is instantaneous. A `Heater Ramp` records its declared duration
on its tuple and moves the running temperature, but the clock does not move
with it — the recipe author is expected to follow every ramp with a matching
`Wait`, and in every example file they do.

**`Pumping` and `Pumping Forward` are complete no-ops, and that is forced, not
an oversight.** Their single parameter is a *target pressure* — `Pumping,
5.00E-01,--`, `Pumping Forward,0.0011,--` — and `params[1]` is always `--`.
There is no number in the row that could be added to the clock, because the
real hold is however long the pump takes to reach that pressure, which depends
on tube state and is not in the recipe. The cost is measured: in the VBBE00
datalog, `Pumping Forward` occupies **844 of 6903 logged samples, about 14
minutes** of wall-clock while contributing 0 s to the reconstructed 7960 s. So
`Timeline.total_time` and every timestamp derived from it are an **idealised
recipe clock, not wall-clock**, and the two diverge by the cumulative pump-down
time before the instant in question. Aligning a reconstructed growth window
against a datalog by absolute seconds will be wrong by exactly that much. Do
not "fix" this by inventing a duration.

One latent bug is reproduced verbatim rather than fixed, and it is flagged
where it lives: `find_growth_window` tests `heater_off_t` for **truthiness**,
so a recipe whose very first command is `Heater Soak` gets `heater_off_t = 0.0`
and no cutoff at all. No example runcard triggers it (every soak is late), and
fixing it would silently change which window this app reports for a file it has
reported on before — a data change, not a display change. The two *display*
guards that had the same shape are fixed instead; see `processing/stats.py`.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..io.parser import RuncardCommand

#: `RuncardCommand` lives with the parser that produces it — this module tree
#: has no `models/` package — so this import runs at module scope and
#: `parser.list_runcards` defers its import of this module instead. See the
#: comment inside `list_runcards`.

CHECK_STATUS_SECONDS = 10
"""Seconds one `Check Status` costs the clock, regardless of its params.

Zero occurrences across all 40 example runcards. It is carried from the CLI
this was ported from, where it was the inline literal `t += 10`, because a
recipe using it would otherwise reconstruct short by 10 s per occurrence with
nothing to say so."""

ROOM_TEMP_C = 25.0
"""Where every reconstructed trace starts and where the cooldown asymptotes.

Not measured per run: the runcard never states an ambient, and the first
`Heater Ramp` states only its target. 25 °C is the CLI's own literal."""

GROWTH_BAND_C = 5.0
"""The growth window is every trace vertex within this of the run-wide peak.

A band rather than a crossing: the reconstructed trace has two vertices per
ramp and no points in between, so an interpolated `peak - 5` crossing would be
a number invented from a straight line nobody measured."""

COOLDOWN_TAU_SEC = 2400
"""Time constant of the synthesized exponential cooldown, in seconds (40 min).

The runcard says nothing about cooling — it only says the heater went off — so
the tail after `Heater Soak` is a model, not data."""

COOLDOWN_STEP_SEC = 60
"""Sampling interval of the cooldown tail, in seconds.

The only uniformly-sampled part of the trace; the ramp phase is a sparse vertex
list."""

#: An MFC must be **strictly above** this to count as flowing. Real runcards
#: idle a channel at exactly `0.01` sccm — a purge flow, not a process flow —
#: so a non-strict test would report every idle channel as on.
_MFC_ON_FLOOR = 0.01

#: Pressure controllers, the throttle valve and the stage must be strictly
#: above zero to count as on. They have no idle offset to clear.
_ZERO_FLOOR = 0.0

#: `(start_s, from_C, to_C, duration_s)`. `from_C` is what the running
#: temperature was when the ramp was issued; `duration_s` is what the recipe
#: *declared*, not what the clock spent.
Ramp = Tuple[float, float, float, float]

#: `(t_s, channel_name, value)` — the channel name verbatim, species suffix
#: included ("MFC-8 H2Se", "PC-1").
NamedEvent = Tuple[float, str, float]

#: `(t_s, value)` for the two single-channel rows, RTV and stage rotation.
ValueEvent = Tuple[float, float]

#: `(t_s, temperature_C)`, a trace vertex.
TracePoint = Tuple[float, float]


@dataclass(frozen=True)
class Timeline:
    """Every command replayed onto the recipe clock, in command order.

    The lists are non-decreasing in `t` because they are appended as the clock
    advances, and simultaneous events share a timestamp: a run of `MFC/PC` rows
    between two `Wait`s all land together. Every consumer here reads them back
    with a last-write-wins scan, which is only correct while that ordering
    holds.

    `frozen=True` blocks attribute rebinding and nothing more — the lists
    themselves stay mutable and are the builder's own. Do not sort them: see
    `build_temp_trace` on why a trace may legitimately run backwards.
    """

    total_time: float
    heater_ramps: List[Ramp]
    p1_ramps: List[Ramp]
    p2_ramps: List[Ramp]
    mfc_events: List[NamedEvent]
    pc_events: List[NamedEvent]
    rtv_events: List[ValueEvent]
    spin_events: List[ValueEvent]
    heater_off_t: Optional[float]


@dataclass(frozen=True)
class GrowthWindow:
    """When the film was actually growing, and how hot it was.

    `peak_temp_c` being a real number is **not** evidence that a window exists.
    It is a `max()` over a trace that always has at least one vertex, so it is
    populated even for a recipe whose final ramp completes after the heater
    went off — which has no window at all. Test `start_s`, never `peak_temp_c`.
    """

    start_s: Optional[float]
    end_s: Optional[float]
    peak_temp_c: float

    @property
    def mid_s(self) -> Optional[float]:
        """Midpoint of the window in seconds, or None if there is no window.

        Every value-at-growth lookup keys off this, so `None` here is what
        makes them all return `None` together instead of quoting a setpoint
        from a run that never reached temperature.
        """
        if self.start_s is None or self.end_s is None:
            return None
        return (self.start_s + self.end_s) / 2

    @property
    def duration_min(self) -> float:
        """Window length in minutes; `0.0` when there is no window.

        Not `None`, which means a caller cannot tell "no window" from a genuine
        zero-length one through this property — a zero-length window is what a
        recipe with no `Heater Soak` produces, since its trace stops at the
        final ramp vertex and both edges land there. Test `start_s` or `mid_s`
        for existence and read this only for display.
        """
        if self.start_s is None or self.end_s is None:
            return 0.0
        return (self.end_s - self.start_s) / 60


@dataclass(frozen=True)
class RuncardProfile:
    """One recipe, fully reconstructed: the single thing every surface reads.

    `temp_trace` is never empty — the worst case is the lone origin vertex
    `[(0.0, 25.0)]` — while `p1_trace` and `p2_trace` are `[]` whenever the
    recipe has no preheater ramps, which is the normal case for HAD* recipes.
    That asymmetry is deliberate and lives in the two trace builders.
    """

    timeline: Timeline
    temp_trace: List[TracePoint]
    p1_trace: List[TracePoint]
    p2_trace: List[TracePoint]
    growth: GrowthWindow


def wait_duration_seconds(cmd: RuncardCommand) -> float:
    """Seconds one `Wait` command holds for.

    **The runcard puts the unit first**: `params[0]` is `Sec` or `Min`,
    `params[1]` is the magnitude. Reading them the other way round reconstructs
    `Wait,Min,20` as 20 seconds instead of 20 minutes, which on a HAD* recipe
    moves the growth window by most of an hour.

    Minutes iff the lowercased unit starts with `min`, so `Min`, `min`,
    `Minutes` and `minute` all scale. **Everything else is seconds**, including
    a typo and including `--` — a silent default, but the alternative is a
    recipe that refuses to load over a unit cell nobody looks at.

    Raises `IndexError` on fewer than two params and `ValueError` on a
    non-numeric magnitude; `list_runcards` is the caller that decides such a
    file is simply not a runcard.
    """
    unit, value = cmd.params[0], cmd.params[1]
    duration = float(value)
    return duration * 60 if unit.lower().startswith("min") else duration


def build_timeline(commands: List[RuncardCommand]) -> Timeline:
    """Replay `commands` onto the recipe clock.

    A single first-match-wins chain with **no `else`**: an unrecognised command
    contributes nothing, silently. That is how `Pumping`, `Pumping Forward`,
    `End` and every row of a mis-fed datalog are dropped, and it is what makes
    `total_time <= 0` a usable "this file is not a recipe" test.

    Four commands read their value out of different columns, and the asymmetry
    is real rather than a mistake to tidy up:

    - `MFC/PC` takes `params[1]` (the channel name is in `params[0]`);
    - `Accumulation PC*` takes `params[0]`, discarding its second param;
    - `RTV Pressure Ctrl` takes `params[1]`, **not** the pressure in
      `params[0]` — see the note on `rtv_events` below;
    - `Stage Rot` takes `params[0]`.

    `RTV Pressure Ctrl,100 Torr,60` stores `60.0`. Across the whole dataset
    `params[0]` is only ever `100 Torr` or `1000 Torr` while `params[1]` ranges
    over {10, 60, 70, 90}, and the measured Tube Pressure during the controlled
    segment of the VBBE00 run is ~7.9 Torr — so the stored number is neither
    the gauge range nor the achieved pressure, and the "Torr" the ancestor
    labelled it with is probably wrong. The arithmetic is reproduced as written
    because it is what every historical figure was drawn from; the label is
    the part to be careful about.

    `Accumulation PC1`/`PC2` are merged into `pc_events` alongside `MFC/PC
    PC-n` rows, so nothing downstream can tell the two sources apart. Both
    spellings are accepted (`Accumulation PC1` and `Accumulation_PC1`) and the
    channel number is every digit left after deleting the literal word
    `Accumulation` — a name with no digits in it yields the channel `"PC-"`.

    Only the **first** `Heater Soak` sets `heater_off_t`; later ones are
    ignored entirely. `HADH00` and `HADG37` each carry two (`Heater Soak,0,--`
    then `Heater Soak,0,600`), and the `600` in the second is not a duration
    the clock consumes — the `Wait,Sec,600` after it does that.
    """
    t = 0.0
    heater_ramps: List[Ramp] = []
    p1_ramps: List[Ramp] = []
    p2_ramps: List[Ramp] = []
    mfc_events: List[NamedEvent] = []
    pc_events: List[NamedEvent] = []
    rtv_events: List[ValueEvent] = []
    spin_events: List[ValueEvent] = []
    heater_off_t: Optional[float] = None
    cur_temp = cur_p1 = cur_p2 = ROOM_TEMP_C

    for cmd in commands:
        name = cmd.name
        if name == "Wait":
            t += wait_duration_seconds(cmd)
        elif name == "Check Status":
            t += CHECK_STATUS_SECONDS
        elif name == "Heater Ramp":
            tgt, dur = float(cmd.params[0]), float(cmd.params[1])
            heater_ramps.append((t, cur_temp, tgt, dur))
            cur_temp = tgt
        elif name == "P1_Heater Ramp":
            tgt, dur = float(cmd.params[0]), float(cmd.params[1])
            p1_ramps.append((t, cur_p1, tgt, dur))
            cur_p1 = tgt
        elif name == "P2_Heater Ramp":
            tgt, dur = float(cmd.params[0]), float(cmd.params[1])
            p2_ramps.append((t, cur_p2, tgt, dur))
            cur_p2 = tgt
        elif name == "Heater Soak":
            # Despite the name this marks the heater going **off**: it is where
            # the synthesized cooldown starts and the hard right edge of the
            # growth window.
            if heater_off_t is None:
                heater_off_t = t
        elif name == "MFC/PC":
            channel, val = cmd.params[0], float(cmd.params[1])
            # Routed on the literal "PC-" prefix rather than a regex, so an
            # unrecognised channel name lands in mfc_events instead of
            # vanishing.
            (pc_events if channel.startswith("PC-") else mfc_events).append((t, channel, val))
        elif name == "RTV Pressure Ctrl":
            rtv_events.append((t, float(cmd.params[1])))
        elif name.startswith("Accumulation PC") or name.startswith("Accumulation_PC"):
            pc_num = "".join(filter(str.isdigit, name.replace("Accumulation", "")))
            pc_events.append((t, f"PC-{pc_num}", float(cmd.params[0])))
        elif name == "Stage Rot":
            spin_events.append((t, float(cmd.params[0])))

    return Timeline(
        total_time=t,
        heater_ramps=heater_ramps,
        p1_ramps=p1_ramps,
        p2_ramps=p2_ramps,
        mfc_events=mfc_events,
        pc_events=pc_events,
        rtv_events=rtv_events,
        spin_events=spin_events,
        heater_off_t=heater_off_t,
    )


def build_temp_trace(ramps: List[Ramp], off_t: Optional[float], total: float) -> List[TracePoint]:
    """The main heater's reconstructed temperature, as a sparse vertex list.

    **Not a uniform sample.** A ramp contributes at most two vertices — a
    plateau at its start carrying the previous temperature, and its end at
    `start + duration` carrying the target — and the straight line between them
    *is* the ramp. Only the cooldown is sampled uniformly. Anything wanting a
    temperature part-way up a ramp has to interpolate; the lookups in this
    module deliberately do not (see `_trace_value_at_or_before`).

    The plateau vertex is emitted only when `pts[-1][0] < ts`, i.e. only when
    there is a gap since the last vertex. The ramp's recorded `from_C` is
    unused: the plateau carries the previous vertex's temperature instead,
    which is the same number in a well-formed recipe and the honest one in a
    malformed one.

    The cooldown starts from `pts[-1][1]`, **the last ramp's target** — taken
    after every ramp is laid down, so if `off_t` somehow precedes the last ramp
    the decay still starts from that later target rather than from the
    temperature at `off_t`. First cooldown vertex at `off_t + 60`, last exactly
    at `total`, so the final step is short whenever `total - off_t` is not a
    multiple of 60.

    **With no `Heater Soak` there is no cooldown and no extension to `total`**:
    the trace simply ends at the final ramp vertex, which may be far short of
    the end of the run. That asymmetry with `build_aux_trace`, which always
    extends, is deliberate — a heater with no off command has no modelled decay
    to draw, and drawing a flat hold out to `total` would assert one.

    Vertices are never sorted or clamped. A ramp whose declared duration runs
    past the next ramp's start emits x-coordinates that go backwards, and every
    consumer here iterates in **list order**, not time order. Real runcards
    pair each ramp with a matching `Wait` so it does not arise; adding a sort
    would change results for files that have never produced one.
    """
    pts: List[TracePoint] = [(0.0, ROOM_TEMP_C)]
    for ts, _t0, t1, dur in ramps:
        if pts[-1][0] < ts:
            pts.append((ts, pts[-1][1]))
        pts.append((ts + dur, t1))
    if off_t is not None:
        last_t = pts[-1][1]
        if pts[-1][0] < off_t:
            pts.append((off_t, last_t))
        tn = off_t
        while tn < total:
            tn += COOLDOWN_STEP_SEC
            tn = min(tn, total)
            pts.append((tn, ROOM_TEMP_C + (last_t - ROOM_TEMP_C) * math.exp(-(tn - off_t) / COOLDOWN_TAU_SEC)))
    return pts


def build_aux_trace(ramps: List[Ramp], total: float) -> List[TracePoint]:
    """A preheater's reconstructed temperature. Three differences from the main one.

    1. **No ramps gives `[]`**, not `[(0.0, 25.0)]`. A recipe with no
       `P1_Heater Ramp` has no P1 to draw, and an origin-only trace would put a
       25 °C line on the plot for a heater that was never addressed.
    2. **No cooldown.** The preheaters get no off command, so they are modelled
       as holding their last setpoint. Synthesizing a decay here would invent
       the one thing the recipe does not say.
    3. **Always extended to `total`**, so the line reaches the right edge of
       the plot instead of stopping at the last ramp.
    """
    if not ramps:
        return []
    pts: List[TracePoint] = [(0.0, ROOM_TEMP_C)]
    for ts, _t0, t1, dur in ramps:
        if pts[-1][0] < ts:
            pts.append((ts, pts[-1][1]))
        pts.append((ts + dur, t1))
    if pts[-1][0] < total:
        pts.append((total, pts[-1][1]))
    return pts


def find_growth_window(temp_trace: List[TracePoint], heater_off_t: Optional[float]) -> GrowthWindow:
    """The stretch of trace within `GROWTH_BAND_C` of the run-wide peak.

    Both edges snap to **trace vertices** and are never interpolated crossings,
    so the start is the vertex at which the final ramp *completes* — not the
    moment the rising ramp passed `peak - 5` — and the end is normally the
    plateau vertex at `heater_off_t`. Verified against the example files:
    VBBE00 gives 2240 s (= 920 + 1320, the second ramp's end) to 3160 s
    (= `heater_off_t`).

    The scan breaks on the first vertex with `t > heater_off_t`, so a vertex at
    exactly `heater_off_t` is inside the window, and `T >= thresh` is
    inclusive.

    Two consequences worth knowing:

    - **A final ramp that completes after the heater went off yields no window
      at all** — the loop breaks before any vertex clears the threshold — while
      `peak_temp_c` still reports that ramp's target. Callers must test
      `start_s`.
    - **`heater_off_t == 0.0` behaves like `None`.** The guard is a truthiness
      test, where `build_temp_trace` correctly uses `is not None`, so a recipe
      whose first command is `Heater Soak` gets a synthesized cooldown but no
      cutoff in this scan. It is reproduced verbatim: no example runcard
      triggers it, and changing it would silently move the window this app
      reports for files it has already reported on.

    Only ever called with a `build_temp_trace` result, which is never empty. An
    empty list would raise `ValueError` out of `max()`; `build_aux_trace`
    output, which *can* be empty, must not be passed here.
    """
    peak = max(temp for _t, temp in temp_trace)
    thresh = peak - GROWTH_BAND_C
    start_s = end_s = None
    for t, temp in temp_trace:
        if heater_off_t and t > heater_off_t:
            break
        if temp >= thresh:
            if start_s is None:
                start_s = t
            end_s = t
    return GrowthWindow(start_s=start_s, end_s=end_s, peak_temp_c=peak)


def build_profile(commands: List[RuncardCommand]) -> RuncardProfile:
    """Commands in, everything the page reads out. The single public entry point.

    The order is fixed: the timeline first because both traces need its clock,
    the main trace before the window because the window is cut out of it, and
    the preheater traces with no `off_t` argument at all — they have no
    cooldown to place.
    """
    timeline = build_timeline(commands)
    temp_trace = build_temp_trace(timeline.heater_ramps, timeline.heater_off_t, timeline.total_time)
    p1_trace = build_aux_trace(timeline.p1_ramps, timeline.total_time)
    p2_trace = build_aux_trace(timeline.p2_ramps, timeline.total_time)
    growth = find_growth_window(temp_trace, timeline.heater_off_t)
    return RuncardProfile(
        timeline=timeline,
        temp_trace=temp_trace,
        p1_trace=p1_trace,
        p2_trace=p2_trace,
        growth=growth,
    )


def get_species(channel_name: str) -> str:
    """The gas a channel name names: its last whitespace-separated token.

    `"MFC-8 H2Se"` gives `"H2Se"`. A single-token name passes through unchanged,
    which is what makes `"PC-1"` answer `"PC-1"` rather than something that
    looks like a species — the pressure controllers carry no gas and must not
    be reachable through a species lookup.

    The *last* token, not the second: `"MFC-3 O2 high"` gives `"high"`. No
    validation, so a malformed channel name yields garbage rather than an
    error; the four species in this dataset are Ar, O2, H2 and H2Se.
    """
    parts = channel_name.split()
    return parts[-1] if len(parts) >= 2 else channel_name


def _first_channel_for_species(events: List[NamedEvent], species: str) -> Optional[str]:
    """The earliest-touched channel carrying `species`, or None.

    First-appearance order, not channel number. It matters when a recipe runs
    one gas on several lines: VBBE00 has Ar on MFC-1, 2, 4 and 5, so a species
    lookup for Ar reports MFC-1 (first event at t=10) alone and says nothing
    about the 170 and 70 sccm carrier flows on MFC-4 and MFC-5. A per-species
    total would be the wrong fix — these are different lines into different
    parts of the tube, and summing them would invent a flow nobody set.
    """
    seen: List[str] = []
    for _t, name, _v in events:
        if name not in seen:
            seen.append(name)
    for name in seen:
        if get_species(name) == species:
            return name
    return None


def _named_event_value_at_or_before(events: List[NamedEvent], name: str, t: float) -> Optional[float]:
    """The last value channel `name` was set to at or before `t`.

    Zero-order hold, last-write-wins, `<=` inclusive: a setpoint stands until
    the next command for that channel. A linear scan of the whole list rather
    than a bisect — these lists are tens of entries, and the scan is correct
    for the duplicate timestamps that a run of simultaneous commands produces
    where a bisect would need a tiebreak rule.

    It cannot tell an `Accumulation PC1`-sourced entry from an `MFC/PC PC-1`
    one; `build_timeline` merges them deliberately.
    """
    value = None
    for et, en, ev in events:
        if en == name and et <= t:
            value = ev
    return value


def _event_value_at_or_before(events: List[ValueEvent], t: float) -> Optional[float]:
    """`_named_event_value_at_or_before` for the two single-channel rows."""
    value = None
    for et, ev in events:
        if et <= t:
            value = ev
    return value


def _trace_value_at_or_before(points: List[TracePoint], t: float) -> Optional[float]:
    """The last trace vertex at or before `t`. A **step** lookup, not interpolation.

    So a `t` part-way up a ramp reads the pre-ramp plateau while the figure
    draws that same stretch as a rising line, and the two disagree. In every
    example file the growth midpoint is well past every preheater ramp, so they
    agree there — but the step semantics are what the numbers on the page have
    always been, and interpolating would quietly change every historical value.
    """
    value = None
    for pt, pv in points:
        if pt <= t:
            value = pv
    return value


def species_value_at_growth_mid(profile: RuncardProfile, species: str) -> Optional[float]:
    """The setpoint of whichever channel first carried `species`, at the growth midpoint.

    `None` on four distinct paths, which the caller cannot tell apart and does
    not need to: no growth window; the species is not in this recipe; the
    channel's first command comes after the midpoint; or the value fails the
    strict `> 0.01` floor. That last one folds "explicitly closed" and "idling
    at purge flow" together with "absent", which is the right answer for a
    column headed with a gas name — none of the three was feeding the growth.

    Searches `mfc_events` only, so `PC-1`/`PC-2` are unreachable here by
    construction.
    """
    mid = profile.growth.mid_s
    if mid is None:
        return None
    channel = _first_channel_for_species(profile.timeline.mfc_events, species)
    if channel is None:
        return None
    value = _named_event_value_at_or_before(profile.timeline.mfc_events, channel, mid)
    return value if value is not None and value > _MFC_ON_FLOOR else None


def channel_value_at_growth_mid(profile: RuncardProfile, channel_name: str) -> Optional[float]:
    """The setpoint of one **named** channel at the growth midpoint.

    Where `species_value_at_growth_mid` answers "what was the Ar doing", this
    answers "what was MFC-4 Ar doing" — which is what a per-channel summary
    needs, since a species lookup reports only the earliest-touched line.

    Routed to `pc_events` or `mfc_events` by the same literal `"PC-"` prefix
    `build_timeline` used to split them, so the routing rule has one home; each
    side keeps its own floor (strictly above 0.01 sccm for an MFC, strictly
    above zero for a controller).
    """
    mid = profile.growth.mid_s
    if mid is None:
        return None
    if channel_name.startswith("PC-"):
        value = _named_event_value_at_or_before(profile.timeline.pc_events, channel_name, mid)
        floor = _ZERO_FLOOR
    else:
        value = _named_event_value_at_or_before(profile.timeline.mfc_events, channel_name, mid)
        floor = _MFC_ON_FLOOR
    return value if value is not None and value > floor else None


def fixed_channel_value_at_growth_mid(profile: RuncardProfile, channel_id: str) -> Optional[float]:
    """The value of one of the seven non-gas channels at the growth midpoint.

    Accepts exactly `Heater`, `P1`, `P2`, `PC-1`, `PC-2`, `RTV`, `Spin`.
    Anything else **raises** rather than returning `None`, because a typo in a
    channel id is a programming error and a silent `None` would show as an
    empty cell indistinguishable from a channel the recipe never used.

    Three asymmetries, all deliberate:

    - **`Heater` ignores the midpoint entirely** and returns the run-wide peak.
      It is the plateau temperature a grower quotes for the run, and sampling
      the trace at the midpoint would return the same number on a well-formed
      recipe and a subtly different one on a ragged trace.
    - **`P1`/`P2` have no floor**, so a genuine 0 °C reads as `0.0`, while a
      zero on PC/RTV/Spin reads as `None`. Those three are off when they are
      zero; a preheater at 0 °C is a reading.
    - The **`mid is None` gate runs before the dispatch**, so an unknown
      `channel_id` on a profile with no growth window returns `None` silently
      instead of raising. Reproduced as-is; it means the raise cannot be relied
      on to catch a typo on every file.

    Mind that `PC-1`/`PC-2` (process pressure controllers, hyphenated) and
    `P1`/`P2` (preheaters, not hyphenated) are four different physical
    channels. Unrelatedly, the datalog column for the *command* `PC-1` is
    `P1 SV`, which is the same collision one layer down.
    """
    mid = profile.growth.mid_s
    if mid is None:
        return None
    tl = profile.timeline
    if channel_id == "Heater":
        return profile.growth.peak_temp_c
    if channel_id == "P1":
        return _trace_value_at_or_before(profile.p1_trace, mid)
    if channel_id == "P2":
        return _trace_value_at_or_before(profile.p2_trace, mid)
    if channel_id in ("PC-1", "PC-2"):
        value = _named_event_value_at_or_before(tl.pc_events, channel_id, mid)
        return value if value is not None and value > _ZERO_FLOOR else None
    if channel_id == "RTV":
        value = _event_value_at_or_before(tl.rtv_events, mid)
        return value if value is not None and value > _ZERO_FLOOR else None
    if channel_id == "Spin":
        value = _event_value_at_or_before(tl.spin_events, mid)
        return value if value is not None and value > _ZERO_FLOOR else None
    raise ValueError(f"Unknown fixed channel: {channel_id!r}")
