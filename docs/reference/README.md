# Vendored references

Source that is a **specification**, not code this project runs. Nothing here is
imported by the app, collected by the test suite, or linted — `pyproject.toml`
excludes this directory from ruff precisely so it can stay byte-identical to
what was handed over, which is the only thing that makes it worth keeping.

Treat these files as read-only. Their value is that they can be diffed against
and run side by side with our implementation; tidying an unused local or
reflowing a comment destroys that.

## `render_runcard.py`

The standalone CLI that draws a runcard's recipe profile as SVG. It is the
authority on recipe semantics for `modules/runcard/`:

- which commands advance the clock, and which are instantaneous;
- how a `Heater Ramp` interacts with the clock it does not spend;
- how the growth window is defined — **exactly** the stretch at the peak, ended
  by whichever comes first of heater-off and a commanded ramp-down;
- the cooldown model (exponential, τ = 1500 s) and the 25 °C ambient;
- that `RTV Pressure Ctrl`'s second column is a gauge range and its third is the
  commanded chamber-pressure setpoint, in Torr;
- that PC-1, PC-2 and every other PC channel stay separate and are never merged;
- the per-species gas palette, and which events are worth marking.

Two things it records that cost this app a bug when they were not carried
across, both noted here so they are not lost again:

1. **The growth window is not a 5 °C band.** The file says so in its own words —
   "not a 'within 5°C' threshold estimate — that was a previously-fixed bug and
   must not be reintroduced". This app reintroduced it by porting an older
   ancestor, and shipped it in v5.1.0 before this file arrived.
2. **Pressure channels hold their last commanded setpoint to the end of the
   run.** An earlier version inferred an end-of-run switch to vacuum from the
   first low `Pumping Forward` value, which also fires during ordinary
   pre-growth evacuation seconds into a run, and that falsely truncated PC-1 and
   PC-2's final segment.

Run it against a recipe to compare:

```
python docs/reference/render_runcard.py <runcard.csv> --out-dir <somewhere>
```

It prints a summary — total time, peak, growth window, per-channel setpoints —
which is what `modules/runcard/` is checked against. At the time of writing the
two agree on total time, peak temperature and growth window for all 40 example
recipes, across both the VBBE and HAD* families.
