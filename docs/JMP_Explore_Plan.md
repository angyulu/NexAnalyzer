# JMP-style exploration in NexAnalyzer

> **Status: a plan, not a spec. Nothing here is implemented.**
> Written 2026-09-14. The measured numbers in *Evidence* were taken from the real workbook
> that day; re-check them before relying on them, and check the code before trusting any
> file path.
>
> **Version numbers shifted once already.** The plan was written expecting the Plot Explorer
> to ship as 4.2.0, but an unrelated 4.3.0 (QC Panel CSV export) shipped from another
> session first. The uncommitted Plot Explorer work is now **4.4.0**, and the plan's stages
> renumbered to match. Re-check `core/version.py` against `git log` before committing —
> this collision can happen again.

## Context

NexAnalyzer just gained a **Plot Explorer** page (v4.4.0, uncommitted): point it at any
`.xlsx`, pick a sheet, drive `plotly.express.scatter` through dropdowns. It exists because
the process data that matters — `Milestone and Schedule.xlsx` — is a hand-kept lab notebook
no generic tool can read: two header rows, three columns all called `H2O`, 14% blank filler
rows, and numbers stored as prose (`1->4(0.2sccm)`, `12min30s`, `35.5-37.5`) in 19 of 38
columns.

The ask is to make that exploration work **like JMP** — all four pillars: Graph Builder,
analysis platforms, a linked data table, and a Local Data Filter. The outcome wanted is
that the question the workbook exists to answer — *does film quality track growth
conditions?* — can be asked directly, with real statistics, instead of eyeballed off a
scatter plot.

## Decisions taken

| Question | Decision |
| --- | --- |
| Separate app, or inside NexAnalyzer? | **Inside**, restructured JMP-style: one shared data table, several platform pages |
| Drag-and-drop Graph Builder | **Spike PyGWalker first**, decide on evidence; build the native pillars regardless |
| First deliverables | **Fit Y by X and Distribution** |
| The uncommitted v4.4.0 work | **Commit it first as a restore point**, restructure on top |

**Why not a separate app.** The hard part is not charting, it is that the spreadsheet is
not tidy. `modules/dataviz/io/excel_source.py` already solves that — 473 lines, zero
Streamlit, fully unit-tested — and a new app rebuilds it. NexAnalyzer also already carries
the double-click installer, auto-updater and launcher aimed at colleagues who never open a
terminal.

**What is and is not natively possible** (verified against Streamlit 1.63, plotly 7.0,
pandas 3.0, statsmodels 0.15):

| Pillar | Native? | Basis |
| --- | --- | --- |
| Analysis platforms | **Yes** | `statsmodels` is already a dependency |
| Linked table + brushing | **Yes** | `st.plotly_chart(on_select=, selection_mode=)` and `st.dataframe(on_select=)` exist — confirmed by introspection |
| Local Data Filter | **Yes** | A richer form of the filter panel already built |
| Graph Builder drag-drop | **No** | Streamlit has no drag-and-drop; needs a component |

---

## Evidence (measured against the real workbook, read-only)

**statsmodels reproduces every JMP table.** Verified on `H2Se (sccm)` vs `T (˚C)`: n=392,
RSquare 0.0621, slope 0.004518, Prob>|t| 5.8e-07. Confidence *and* prediction bands come
from `get_prediction(...).summary_frame()` as `mean_ci_*` / `obs_ci_*`.

**The guard cases are the user's primary question, not hypotheticals.** `FWHM (E2g)` and
`LA/E2g` hold **5 non-null values of 602**, and **all five were measured at exactly
T = 900 ˚C**. Measured consequences:

- `sm.add_constant(x)` returns a **(5, 1)** design — x is constant, so it refuses to add a
  collinear intercept.
- `sm.OLS(...).fit()` still "succeeds": one meaningless parameter, `RSquare = -0.0000`,
  and **`Prob>|t| = 0.0015`** — a significant-looking p-value on a model that does not
  exist. No exception, no warning.
- A naive implementation reading `params[1]` raises `IndexError`.

So Fit Y by X must gate on minimum N **and** at least two distinct X values, and say which
failed. The honest message is not "error" but *"every FWHM you have recorded was measured
at 900 ˚C, so this relationship cannot be estimated yet"* — a data-collection fact worth
surfacing.

**Today the only platform that yields an answer is Oneway.** `Result_PL (FWHM)` coerced
with `midpoint` gives n=76 against `T`, across 3 distinct temperatures (890×40, 950×19,
900×17). That is a three-level Oneway, not a regression.

**Every process column is a setpoint.** Distinct counts after `leading` coercion: `T` 14,
`P` 14, `Time` 12, `H2Se` 6, `Dist.` 7, `Ar out` 3. Two consequences: Oneway is the natural
platform for most X, and JMP's **Lack Of Fit** table will genuinely appear and genuinely
inform — it separates "a straight line is the wrong shape" from "runs at the same setpoint
scatter this much".

**Navigation supports the needed shape.** `st.navigation` accepts
`Mapping[SectionHeader, Sequence[Page]]`, and a flat list compiles internally to
`{"": pages}` ([navigation.py:342](venv/Lib/site-packages/streamlit/commands/navigation.py#L342)).
So `{"": [1-4], "Explore": [5-8]}` renders the existing four pages byte-identically.

---

## Sequencing

| Release | Content | Property |
| --- | --- | --- |
| **v4.4.0** | Commit the Plot Explorer exactly as it stands | Restore point; 555 tests green |
| **v4.5.0** | Restructure only: split into Data Table + Graph Builder, add the Explore section | **Behaviour-preserving** — independently verifiable |
| **v4.6.0** | Distribution + Fit Y by X | Features on a stable base |
| *(parallel)* | PyGWalker spike in a throwaway venv | Gates the Graph Builder question |

Splitting v4.5.0 from v4.6.0 matters: the restructure touches every file the current work
added, and it is far easier to tell "the split broke it" from "the statistics broke it"
when they are separate commits.

---

## v4.5.0 — the restructure

### Session state holds the *recipe*, never the DataFrame

```python
st.session_state["dataviz"] = {
    "table": {"path": None, "sheet": None, "header_rows": 1,
              "coercions": {}, "filters": [], "modeling_types": {}},
    "platforms": {"graph_builder": {...}, "distribution": {...}, "fit_y_by_x": {...}},
    "_saved": None,
}
```

The frame is re-derived per page run: the Excel parse comes from a shared `@st.cache_data`
keyed on `(path, mtime, sheet, header_rows)`; coerce+filter runs fresh (sub-millisecond at
600 rows).

Storing the frame in session state would need an explicit "drop the derived frame" call at
every site mutating the recipe — and this repo already carries that bug's fossil in
`modules/optical/ui/qc_panel_state.py::reset_results`, whose docstring says the Sample
Report page "learned this the hard way". A cache keyed on the recipe cannot go stale,
because the key *is* the recipe. `cache_data` also returns a copy, so one page cannot
corrupt another's frame.

**New hard invariant.** Streamlit garbage-collects widget state for widgets not rendered on
the last run — absolute across pages. **The session dict is the truth; widgets are re-seeded
from it every run and never read back across a page boundary.** The current page already
does this; it stops being a nicety and becomes a rule.

### The extraction

`modules/dataviz/processing/` — new subpackage mirroring `modules/spectra/processing/`
(the repo's existing home for "numbers, no UI"). No Streamlit, no plotly.

```python
# processing/table.py
class DataTable(NamedTuple):
    frame: pd.DataFrame       # coerced + filtered — what every platform consumes
    source: pd.DataFrame      # header-joined, blanks dropped, pre-coercion
    profiles: List[ColumnProfile]
    losses: Dict[str, int]
    kept: int
    total: int

def build_table(frame: pd.DataFrame, state: Mapping) -> DataTable: ...
```

It takes the frame *separately* from the state because reading is IO and caching is
Streamlit's job — that is what makes the unit test a three-line DataFrame instead of a
temp `.xlsx`. A new module rather than an addition to `excel_source.py`, so
`tests/unit/test_excel_source.py` stays green **by construction**.

Streamlit-facing helpers go in `modules/dataviz/ui/table_state.py`: `current_table(state)`
and `require_table(state)` — the latter is one line at the top of each platform page
rendering a guard, an `st.page_link` back to Data Table, and `st.stop()`.

### Pages and navigation

| Page | Content |
| --- | --- |
| `pages/5_Data_Table.py` | Lines 77–353 of today's page verbatim: workbook picker, Reload, Header rows, sheet picker, column profile + coercion, row filters — **plus a read-only `st.dataframe` preview** |
| `pages/6_Graph_Builder.py` | Lines 355–535 verbatim: four expanders, `build_scatter`, `render_plot`, PNG/HTML export, behind `require_table` |

```python
nav = st.navigation({"": [spectra, sample_report, presets, qc_panel],
                     "Explore": [data_table, graph_builder]})
```

Pages 1–4 are **not** renumbered and render identically. The `app.py` docstring currently
argues against sections and that must be answered, not silently contradicted: `"Raman & PL"`
died because it was a **claim about technique** that stopped being true. `"Explore"` states a
**dependency** — those pages share one loaded table and are inert until it is loaded. That
will not stop being true. The first group stays unlabelled for the same reason the old
label died.

A section header cannot tell a user their table is unloaded, so `require_table`'s page link
plus a caption naming the live sheet are what actually carry the dependency.

### Persistence and keys

One file, still `data/plot_explorer.json`, still keyed by sheet name (sheets share almost
no column names — that argument strengthens with three platforms each naming columns).
`SCHEMA_VERSION` 1 → 2, nested `{"table": {...}, "platforms": {...}}` — exactly the session
shape minus `path`. **No migration:** the loader already discards documents it does not
recognise and the installed base is zero.

`prune_to_columns` currently hardcodes `scatter.py`'s role list inside `io/config_store.py`
— a layering smell where adding a scatter role means editing another subpackage. It
generalizes to `prune_config(config, columns, roles, list_roles)`, each viz module
declaring its own `COLUMN_ROLES`.

`K()` moves to `modules/dataviz/ui/keys.py` as `key_factory(state, platform)` producing
`dv::{platform}::{path}::{sheet}::{name}`. **The platform segment is load-bearing:**
Distribution and Fit Y by X both want a control called `x`, and Streamlit stores widget
values under the literal key string. A cross-page collision does not raise
`DuplicateWidgetID` — that check is within one run — it silently restores the other page's
value.

### Order of work (suite green at every step but one)

| Step | Action | Suite |
| --- | --- | --- |
| 1 | Add `processing/table.py` + its unit test | green (nothing imports it) |
| 2 | `io/config_store.py` → v2 doc, `prune_config`, narrow writers; keep `prune_to_columns` as a shim | green |
| 3 | Lift `_cached_sheets`/`_cached_frame`/`_mtime` → `ui/table_state.py`, `K` → `ui/keys.py`, `NONE_LABEL`/`_column_select` → `ui/widgets.py`; repoint the existing page | green — no labels change |
| 4 | Create both new pages, reshape `ui/state.py`, update `app.py`, split the integration test, delete `pages/5_Plot_Explorer.py` | **the one breaking step; atomic** |
| 5 | Drop the `prune_to_columns` shim; docs, version, CHANGELOG | green |

`tests/unit/test_excel_source.py`, `test_dataviz_scatter.py` and `io/excel_source.py` are
**never touched**.

Splitting the integration test forces an improvement: `TestSwitchingSheets` currently
asserts that changing the sheet changes *Graph Builder's* X dropdown, which becomes
cross-page and undrivable. Reassert on the Data Table preview's columns and on
`session_state["dataviz"]["table"]["sheet"]` — strictly better, because it tests that the
table changed rather than that one consumer noticed.

---

## v4.6.0 — Distribution and Fit Y by X

New pure modules under `modules/dataviz/processing/`: `modeling.py`, `distribution.py`,
`bivariate.py`, `oneway.py`, `formatting.py`. New figure builders under `viz/`:
`dist_plot.py`, `fit_plot.py`, `oneway_plot.py`. Pages `7_Distribution.py` and
`8_Fit_Y_by_X.py` join the Explore section.

### The five traps that decide whether this matches JMP

These are the things that look right and are wrong. Each gets a pinned test.

1. **Quantiles.** JMP uses `rank = p(n+1)/100` — Hyndman–Fan **type 6**, i.e.
   `np.quantile(x, q, method="weibull")`. **pandas cannot do this**; its default is type 7.
   Measured on `[1,2,3,4,5]`: weibull 25% = **1.5**, pandas = **2.0**. The box plot must be
   fed these same precomputed quartiles via `go.Box(q1=, median=, q3=, lowerfence=,
   upperfence=)` so the picture and the table cannot disagree.
2. **`np.std(x, ddof=1)`.** `ddof=1` is not a default anywhere in numpy.
3. **The 95% mean interval uses Student's t, not 1.96.** At n=5 the multiplier is 2.7764 —
   42% wider — and n=5 is exactly what `FWHM (E2g)` gives today.
4. **`sm.add_constant(..., has_constant="add")`.** The default `"skip"` produces the
   silent (5,1) design documented in Evidence above.
5. **`res.ssr` is the *Error* row; `res.ess` is the *Model* row.** statsmodels names these
   opposite to much of the literature. Swap them and R² disagrees with the SS column — the
   kind of error that survives review. Test both `Model + Error == C. Total` **and**
   `Model / C. Total == rsquare`; the first passes even when swapped.

Also: use `sm.OLS`, **not** `smf.ols`. The columns are named `T (˚C)` and
`LA/E2g (relative intensity)`; `/` and `()` are formula operators, and the required
`Q("...")` wrapper leaks into the Parameter Estimates table where JMP writes the plain name.

### Distribution

Dispatch on `ColumnProfile.kind`: numeric → continuous; text → categorical; **mixed →
categorical by default, with inline coercion offered**; datetime excluded in v1; empty →
an empty-state card.

Refusing mixed columns would refuse half the sheet including `T` and `P`. Auto-coercing
would undo `excel_source`'s own deliberate decision that no strategy is the default
"because `1->4` means the flow was *ramped*". So: show the Frequencies table immediately —
which is often *diagnostic* (measured: `T (˚C)`'s 65 text cells are the strings `'890'` and
`'950'`, numbers typed as text) — and offer coercion above it, reusing the existing picker
from `pages/5_Plot_Explorer.py:221-279`. Once chosen, keep a **permanent caption inside the
report panel**, because the report is what gets screenshotted into a slide.

Panels match JMP: **Quantiles** (11 rows, max first, four tagged) and **Summary
Statistics** (Mean, Std Dev, Std Err Mean, Upper 95% Mean, Lower 95% Mean, N — Upper before
Lower). One deliberate departure: promote **N Missing** into the default rows. JMP hides it;
the defining property of this workbook is emptiness.

Build: outlier box plot above the histogram (JMP's default), a bin-count control, and a
normal quantile plot behind a toggle. **Skip Shapiro–Wilk** — at n=445 it rejects normality
on any real process column and reads as "my data is bad"; at n=5 it never rejects and reads
as "my data is normal". Gate any fitted-normal overlay at n ≥ 20, off by default.

Cap categorical levels at 30 (`WaferID` has 444 distinct in 529 rows) with an
`Other (414 levels)` row.

### Fit Y by X

**Bivariate first, Oneway second, Contingency deferred, Logistic never.** One platform with
a dispatch on modeling types, as JMP does — so "flip `H2Se` to categorical and look at the
Oneway" is a click, not a navigation.

Bivariate renders **Linear Fit**, **Summary of Fit**, **Analysis of Variance**, **Parameter
Estimates** (plus `Lower 95%`/`Upper 95%` from `res.conf_int()` — a slope whose CI spans
zero is far more legible than `p = 0.31`), **Lack Of Fit** when X is replicated, and **Fit
Mean**. Confidence band on by default, prediction band off, matching JMP.

Oneway's detail that implementations get wrong: JMP's "Means for Oneway Anova" uses the
**pooled** standard error `RMSE/sqrt(n_i)` with `t(0.975, n-k)` — *not* each group's own SD.
Its separate "Means and Std Deviations" table is the unpooled one. Ship both with JMP's
labels, or a user checking one number concludes the platform is broken. Compute the ANOVA
from a dummy-coded `sm.OLS` rather than `scipy.stats.f_oneway`, so Summary of Fit falls out
of the same object as the F ratio.

**Guards** — run *before* `.fit()`, since neither failure raises:

| Gate | Threshold | Behaviour |
| --- | --- | --- |
| Pairwise-complete N | `n < 3` | No fit |
| **X variance** | `distinct_x < 2` | **No fit** — the one that fires today |
| Y variance | `distinct_y < 2` | No fit |
| Distinct X | `< 3` | Fit, with a note |
| Small N | `3 <= n < 8` | **Fit, but banner it.** Suppress nothing |

A refusal **is a result**, not an exception — it returns a plotted scatter plus the counts
table that names the cell to go fill in. Returning `Union[BivariateFit, Refusal]` keeps its
rendering out of the page's `except` block.

**Coercion provenance is not optional.** `H2Se (sccm)` has 59 text cells like
`2->4(0.5sccm per 30s)`; `leading` reads 2, `midpoint` reads 3, and neither is what
happened. Make coercion an argument to the pure fit function so the result carries
`x_coercion`/`x_lost`, render a `Column Notes` table under Parameter Estimates, and escalate
to a visible warning above the plot when loss exceeds 10% of a column's filled count
(measured: `T (˚C)` at 65/445 = 15% trips this).

**Multiplicity: count, don't preach.** Say nothing for four fits; from the fifth, one
footer line of arithmetic — *"This is the 7th X column fitted against 'FWHM (E2g)' this
session. At p < 0.05 across 7 tests the chance of at least one false positive is ~30%. A
Bonferroni threshold for 7 tests is p < 0.0071."* No modal, no red, no advice. Do **not**
auto-adjust the displayed p-value (it stops being JMP's number) and do **not** build an
all-pairs screening matrix.

### Rendering

`st.dataframe(..., hide_index=True)` fed **strings** from `formatting.py`, never raw floats
— Streamlit would render `p = 4.59e-07` as `0.0000`, and a p-value of zero is a lie. JMP
prints `<.0001`. Plot first at full width through `render_plot`, then Quantiles and Summary
Statistics side by side under plain markdown headers (JMP's outline nodes are open by
default; the point is seeing it all at once). One "Copy as text" `st.code` block behind an
expander per platform gives the fixed-width JMP look for pasting into email.

---

## The PyGWalker spike (throwaway venv, never `venv/`, `requirements.txt` untouched)

PyGWalker is the only realistic route to true drag-and-drop. Its metadata brings `duckdb`,
`sqlglot`, `sqlalchemy`, `pyarrow`, `pydantic`, `ipywidgets`, `anywidget` — and
**`kanaries-track==0.0.5`** plus **`segment-analytics-python==2.2.3`**. It does *not* pin
Streamlit, which is the key relief: `start.bat:98` runs `pip install -r requirements.txt`
on **every launch** and `exit /b 1` on failure, so a component pinning `streamlit<1.x`
would stop the app launching for every user.

Four gates, in priority order:

1. **Telemetry goes quiet.** `pygwalker config --set privacy=offline`, then verify nothing
   is sent. NexAnalyzer processes TSMC customer wafer data — a policy question, not a
   preference. **If it cannot be silenced, stop here.**
2. **Renders with no internet.** The repo already treats a CDN dependency at open time as a
   defect worth 3 MB to avoid, and corporate proxies are documented in `USER_GUIDE.md`.
3. **Windows path length.** `Install-NexAnalyzer.bat` rejects install paths over 100 chars
   (pywin32 unpacks deep enough for `WinError 206`). The venv already reaches **163 chars**
   below the install dir — at a 100-char install path that is 263, past Windows' 260 limit.
   A deep component tree worsens an existing latent risk.
4. **Useful on the real data** — feed it `read_sheet` + `apply_coercions` output for
   `HA_SplitTable`.

Accepted cost on success: `AppTest` cannot drive custom-component frontends, so that page
leaves the test harness. Tolerable for an exploratory surface, **not** for Data Table —
which is why loading, coercion and filtering stay on native widgets regardless.

Fallback if it fails: a JMP-shaped panel from native widgets — column list plus role
shelves (X, Y, Color, Size, Group, Wrap) and a live chart. Click-to-assign rather than drag,
fully testable, no new dependency.

---

## Verification

**v4.4.0 commit.** `pytest` — expect **555 passed** in ~2.5 min, and `python -m ruff check .`
clean. Run it while the machine is awake: a run spanning a sleep fails a random AppTest test
on timeout (see `~/.claude/.../memory/pytest-sleep-false-failures.md`).

**v4.5.0 restructure.** Behaviour-preserving, so the bar is that the split changed nothing:
- `pytest` green at every step in the table above except step 4.
- Launch `streamlit run app.py`; confirm the sidebar shows pages 1–4 unlabelled with a
  collapsible **Explore** group, and that pages 1–4 look untouched.
- Load `Milestone and Schedule.xlsx`, `HA_SplitTable`, Header rows = 2. Confirm the Data
  Table preview shows 516 rows × 38 columns with `H2O (sccm)`, `H2O (sccm) #2`,
  `H2O (torr)`, `FWHM (E2g)`.
- Navigate to Graph Builder **without** reloading; confirm it sees the same table and that
  the caption names `HA_SplitTable`. Then visit it with nothing loaded and confirm the
  `require_table` guard and page link.
- Switch to `QUAD_SplitTable` and back; confirm columns follow and no stale axis survives.

**v4.6.0 platforms.** The pinned numbers are the test:
- Unit: the `[1,2,3,4,5]` quantile case (25% = 1.5, *not* pandas' 2.0); `std_dev` =
  1.5811388 not 1.4142; the n=5 CI half-width = 2.7764 × sem; the eight-point regression
  locked to 6 significant figures; `Model + Error == C. Total` **and**
  `Model / C. Total == rsquare`.
- **The single most important test:** the five real `FWHM (E2g)` values (3.21, 2.89, 1.456,
  2.73, 2.05) against five `T = 900` must return a `Refusal` naming both columns and the
  value 900, with `both_filled == 5` and `distinct_x == 1`. Its docstring records that
  `sm.OLS` returns `Prob>|t| = 0.0015` here with no warning, so nobody simplifies the guard
  away.
- A source-level test asserting nothing under `processing/` imports `streamlit` or
  `plotly`. The whole value of that layer is being testable without a browser, and that is
  one careless import away from gone.
- End-to-end: open Fit Y by X, pick Y = `FWHM (E2g)`, X = `T (˚C)`, and confirm it shows the
  refusal and counts table rather than a plausible-looking line. Then Y =
  `Result_PL (FWHM)` with `midpoint` coercion, X = `T (˚C)` as **categorical**, and confirm a
  three-level Oneway with group sizes 40/19/17.

**Cross-tool oracle worth doing once:** paste the eight-point fixture into real JMP and
confirm the numbers match. That turns the regression test from a self-consistency pin into
evidence the platform actually agrees with JMP.
