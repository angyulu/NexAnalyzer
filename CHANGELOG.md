# Changelog

All notable changes to NexAnalyzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0] - 2026-09-18

### Changed

- **The Sample Report and QC Panel pages are merged into one QC Report page**
  (`pages/2_QC_Report.py`). They read the same sample folder, ran the same scan
  and the same fit, and each produced half of what an operator wanted — so
  running both meant picking the same folder twice and fitting the same spectra
  twice, with two chances for the two halves to describe different fits of one
  sample. One folder pick, one `run_sample_batch`, and every artifact derived
  from that single result. Plot Explorer moves from page 5 to page 4; the nav
  is four pages now, not five.

- **Seven numbered figures and one workbook replace the three-slide deck.**
  `_1_Summary`, `_2_OM`, `_3_OM_diagnostic`, `_4_Raman`, `_5_Raman_stats`,
  `_6_PL`, `_7_PL_stats`, plus the `.xlsx`. The numeric prefix is load-bearing:
  alphabetical sort puts "Summary" last and interleaves the two techniques, so
  a colleague handed the folder would meet the figures in an order nobody
  chose. The summary page keeps the old slide 1's content — title bar, the 3x3
  grid of raw OM frames, the Raman and PL fit-summary tables — and gains the
  per-class segmentation table beneath the grid, in the 1.7 inches the slide
  left blank.

- **The workbook carries every table.** `Summary`, `Raman`, `PL`, `OM_Stats`,
  `OM_Points`. The four CSVs the two pages wrote between them are retired; two
  of them were near-duplicates of sheets the workbook already had (the
  per-point fit table and the per-peak aggregate), which was one more way for
  two files to disagree about one measurement.

- **`raman_quality.py` is now `peak_quality.py`, and serves both techniques.**
  The drawing never knew anything about Raman — it reads `peak.label`,
  `peak.center`, `peak.width_fwhm` and `peak_intensity(peak)`, all of which
  exist identically on a PL fit. Everything technique-specific is now a
  `QualityFigureSpec` value carrying the panel columns, the cleaning rule and
  the marker statistic together, so a call site cannot pair Raman's panels with
  PL's cleaning. The grid is computed from the columns rather than hardcoded:
  the old `GridSpec(2, 3)` silently dropped a third panel in any column and
  raised `IndexError` on a fourth column.

- **Per-position markers: mean for Raman, median for PL.** Each technique's
  ancestor uses its own, and the PL summary schema stores medians only. The
  statistic is named in the figure's suptitle, because the difference is
  invisible in the mark itself and silently moves every point on the figure.

- **PL cleaning is PL's own rule, not Raman's.** Raman keeps the 1.5x IQR cut
  within each position, matching `peak_metrics.aggregate_fit_results` so the
  figure and the summary tables cannot show two numbers for one measurement. PL
  takes the inherited rule instead: `FWHM > 5 nm`, `Center > 700 nm`, then the
  widest 5% of each peak's fits dropped across the sample. Both run downstream
  of the same R-squared gate.

- **The diagnostic ratio pairs have one home.** `peak_metrics.RAMAN_RATIO_PAIRS`
  — `LA/E2g+A1g` and `C/LB`. They were two independent literals, one in the
  figure and one in the page, each with a comment saying they had to agree.

- **Version 5.0.0, not 4.7.0.** A page is gone, the output formats changed, and
  two dependencies were dropped. Muscle memory and old file expectations both
  break.

### Added

- **PL quality panels** (`PL_PANEL_COLUMNS`), ported from the `WSe2_PL.py`
  ancestor: FWHM and centre for Exciton and Trion, plus the Exciton/Trion
  **intensity** ratio. (The ancestor's fit table calls that column "Amplitude",
  but it holds peak height, which is what this codebase calls intensity — see
  CLAUDE.md. Reading it as lmfit's `amplitude`, the integral, would give a
  different number, since Exciton and Trion have materially different widths.)
  The ratio column holds one panel where the others hold two, and that gap is
  deliberate — the lineage defines exactly one PL ratio, and filling the slot
  would mean inventing a second or moving an intensity panel into a column
  titled "Diagnostic Ratios".

- **One PL spec line: 35 nm FWHM**, drawn on both the Exciton and Trion panels,
  from `WSe2_PL.py` where the sibling wafer-comparison script labels it
  "FWHM = 35 (Spec)". There is deliberately **no PL centre spec and no PL ratio
  spec**: the ancestor gates its only PL reference line on `if col == "FWHM"`,
  and the 770/800 nm in the material preset are fit-initialisation guesses, not
  tolerances anyone measured. The unity line the ancestor draws on the PL ratio
  is grey dotted with no legend entry and is never called a spec, unlike every
  line it does label "(Spec)" — so it is left out too.

- **A pre-run inventory.** Above the Run button: `9 OM (100x) · 9 Raman · 0 PL`.
  A folder whose PL files are named `PL1.txt` instead of `PL_1.txt` scans as a
  sample with no PL and is indistinguishable from one that genuinely has none
  once the report is built. Two absences get two different sentences, because
  they are fixed in two different places: no files in the folder is a naming
  problem, a material with no PL block is a preset problem.

- **A quality-gate verdict per technique**, and no combined pass/fail. PL
  carries one spec line and no centre or ratio spec, so an overall grade would
  assert a judgment the data cannot support.

- **`core.report.models.OpticalClassStat`** — the optical counterpart of
  `PeakStat`, so the summary figure can print the segmentation's class table
  next to the Raman and PL ones without `core` importing `modules.optical`.

- **`WSe2-HA` is folded into `WSe2`; the old `WSe2` entry is gone.** The two
  presets were byte-identical apart from their optical block — `WSe2-HA` added
  `abs_threshold_below: 6.0` / `abs_threshold_above: 4.25`, switching the
  segmentation from the adaptive `nsigma` rule to a fixed green contrast. There
  is now one WSe2 preset and it carries that pair, so fixed contrast is the
  default for WSe2 work rather than an alternative to it. **This changes
  segmentation results for anyone who was selecting plain `WSe2`**: coverage
  percentages move, because the cut moves. A material that wants the adaptive
  rule back simply omits the pair. `data/materials.json` is committed and
  shared, so this reaches every clone on the next pull.

### Fixed

- **The summary page's table columns could overlap.** Centred text in a
  matplotlib axes is not clipped to anything, so a cell wider than its column
  drew straight across its neighbour: a real WSe2 PL table printed
  `41022.4 ± 3980.31.4 ± 2.0`, the Intensity value running through the FWHM
  one. The PowerPoint table this replaced auto-shrank its own cell text.
  `_fit_font_size` now measures every cell and shrinks the table's font until
  all of them fit, with a 7pt floor — past that the value itself is the problem
  and should be caught in review. Found by rendering a page and looking at it;
  every test passed throughout, because they asserted PNG magic bytes.

- **One unreadable optical frame no longer discards the whole report.**
  `analyse_frame` was called unguarded, so a corrupt, truncated, locked or
  cloud-only image raised through every later stage. The QC Panel had the same
  hole, but it only cost that page's two figures; with one run producing
  everything, it would have cost all seven and the workbook — including the
  Raman and PL halves, which have nothing to do with the bad frame. A frame
  that cannot be segmented now drops out with a warning and the rest of the
  sample still reports.

- **Changing the OM magnification now drops the other group's results.** The
  selectbox wrote straight into state with no reset, so a folder holding both
  `50x_1..9` and `100x_1..9` would keep showing — and saving — the 50x
  segmentation under a summary page whose grid caption reads "OM (100x)".
  Inherited from the QC Panel, where the same selectbox had the same gap.

- **A run that loses every fit at the quality gate is no longer invisible to
  the staleness check.** The check was keyed on the stats figure, which that
  run does not produce — so the one case whose whole point is that the operator
  goes and fixes the preset was the one case where coming back with a fixed
  preset changed nothing on screen. The preset fingerprint is now stamped on
  attempt rather than on success.

- **The Material Presets page no longer directs users to two pages that do not
  exist.** Its body text still named the Sample Report and the QC Panel, and
  called the Spectra page "the Analysis page".

### Removed

- **`core/report/pptx.py` and `core/report/slides.py`**, and with them
  `python-pptx` and `pywin32` from `requirements.txt`. Nothing in the app needs
  Microsoft Office installed any more. `_hex_to_rgb` moved to
  `core/report/summary_figure.py`: the summary page draws the same fit legend
  the slide did, so the `#RRGGBB`-only rule in `modules/spectra/viz/palette.py`
  still has teeth — matplotlib would accept a CSS name happily, and the strict
  parser is the only thing that notices.

- **`modules/optical/io/frame_csv.py`** — replaced by `frame_tables.py`, which
  returns rows instead of CSV text.

- **`export_point_fits_csv` and `export_peak_stats_csv`** from
  `modules/spectra/io/results_csv.py`. The master and per-file CSVs stay.

### Notes

- **The progress weights are owed a re-measurement.** The report half was
  measured on a real 9-point sample; the segmentation half comes from the QC
  Panel's own documented timings (~30 s for nine frames, ~5 s per OM render).
  The two came off different samples on different days, so only their ratio to
  each other is guesswork. The shape is not: segmentation is far and away the
  longest stage at ~47% of a ~64 s run, and a bar that doesn't say so sits
  nearly still for half a minute.

- **`USAGE.md` in the inherited analysis repo documents the PL FWHM floor as
  20 nm.** That is the default for its "Raw" pseudo-peak; Exciton and Trion
  explicitly override it to 5. The 5 is what this port uses.

## [4.6.0] - 2026-09-15

### Added

- **`threshold_mode="midpoint"` for the OM segmentation.** A third rule for
  placing the two cuts, beside the adaptive `nsigma` rule and v4.4.0's fixed
  contrast pair, and the first that needs no number typed in. It measures the
  plateau of whatever lies beyond the adaptive cut on each side -- the next
  layer's brightness, in the sample's own frame -- and places the boundary
  halfway between that and the film mode, which is the Bayes boundary between
  two populations of equal noise. Measured, not asserted: the asymmetry
  between the two sides (one layer step up, several down) falls out, and a
  1L-reference sample or a different oxide gets its own step without a preset
  edit. Selectable per material and layer in the preset editor
  (`threshold mode`), stored as `OpticalParams.threshold_mode`; unset keeps
  the old behaviour exactly, including "pair set means absolute".

  One pass, not an iteration. Re-measuring the plateau at each tighter cut
  was tried and rejected on HADH37: every tighter cut admits more of the
  film's own tail, the plateau drifts toward the cut, and the rule walks the
  threshold into the film's shoulder (Above 2L 2.2 % -> 7.4 % on a frame with
  visibly few bright domains). Measured once beyond 4 sigma the step is the
  domain interior and the truncation bias is negligible for anything
  resolvable.

- **Two honest non-answers, and they are printed.** A side holding under
  0.1 % of the frame beyond the adaptive cut has no population (`empty`) and
  keeps that cut. A side whose half-step is under 2.5 noise sigmas is a
  boundary the film's own tail would cross (`noise-limited`): the adaptive cut
  is kept and the coverage it yields is a *lower bound*, marked `>=` on the
  figure panel, listed in the histogram box, counted in the title and in a
  new `N_Noise_Limited` column of the stats CSV. The points CSV gains
  `Threshold_Mode`, `Step_Below_pct`, `Step_Above_pct`, `Status_Below`,
  `Status_Above`, so a coverage number can always be traced to the rule and
  the measured step that produced it. This is what v4.4.0's "validity gate"
  paragraph asked the reader to compute by hand.

  Why 2.5: with `nsigma` 4, a population entirely hidden inside the cut
  measures a truncated tail whose mean sits ~0.3-0.5 sigma past the cut, so
  its half-step comes out at 2.15-2.25 sigma. The gate sits just above what
  nothing-there produces, which is what makes it a detector of "there is a
  plateau" rather than a tuning number.

### Changed

- On HADH37 (nine 50x frames, 2L reference) the three rules give Bilayer
  93.4 +- 4.1 % (adaptive), 95.8 +- 4.0 % (absolute -6/+4.25) and the midpoint
  cuts land at -4.5 to -5.5 % / +3.1 to +3.7 % from the measured steps. On P7,
  the frame whose widened noise had pushed the adaptive cut to +5 %, Above 2L
  goes 0.4 % -> 1.3 %: the population the adaptive rule hid. On HADG37, whose
  "noise" is 16-41 % of the mode, every side reads `empty`, the adaptive cut
  stands and Bilayer stays 99.96 % -- where the fixed pair reports 52 %.
  No preset was switched: `WSe2` keeps `nsigma`, `WSe2-HA` keeps its pair.
  Numbers move only where a preset opts in.

### Notes

- The adaptive rule's golden numbers in `tests/unit/test_om_contrast.py` are
  unchanged; the midpoint rule gets its own. `OpticalParams` presets written
  by v4.4.0 load and behave identically.
- Known limit, shared with the rest of the module: two populations on one
  side (1L and bare substrate under a 2L film) are not separated. The
  plateau is their area-weighted mean and the cut lands at half of that,
  which can split the nearer one; the histogram row shows it.

## [4.5.0] - 2026-09-14

### Added

- **Plot Explorer page.** A fifth page that plots any `.xlsx` through
  `plotly.express.scatter`. It is deliberately schema-blind -- it knows nothing
  about peaks, spectra, material presets or the app's own `.xlsx` export -- so
  the hand-kept process workbooks that hold run conditions are readable as they
  stand, without being cleaned first. New package `modules/dataviz/`, which is
  the first one under `modules/` that is not a measurement technique.

  One sheet at a time, never several combined: one plot draws on one tool's
  runs, and a scatter mixing two tools' chemistries onto one axis would imply a
  comparison that isn't valid. The sheet picker shows each sheet's populated row
  count, so a 99%-blank template sheet reads as "5 rows" instead of looking like
  a broken plot.

  Controls cover `x`, `y`, `color`, `symbol`, `size`, `size_max`, `opacity`,
  `hover_name`, `hover_data`, `facet_row`, `facet_col`, `facet_col_wrap`,
  `error_x`, `error_y`, `marginal_x`, `marginal_y`, `trendline`, `log_x`,
  `log_y`, `range_x`, `range_y`, `template` and `title`, grouped into four
  expanders above a full-width plot. `size` offers numeric columns only, since
  a text column there is a Plotly exception rather than a bad-looking chart; a
  facet over 30 distinct values or a discrete colour over 20 warns and plots
  anyway, since 40 facets is occasionally what was wanted.

- **Two header rows, joined into column names.** A `Header rows` setting (1 by
  default). Set to 2, a sheet whose row 1 names the column and row 2 qualifies
  it yields `H2O (torr)`, `FWHM (E2g)` rather than a first data row full of the
  string `"torr"` and every numeric column typed as text. It is also what
  separates three columns all called `H2O`; whatever still collides is suffixed
  `#2` rather than pandas' `.1`, which reads like part of the name. Columns with
  no header at all are dropped as spacers, and entirely blank rows are dropped
  on load.

- **Per-column numeric coercion, with a preview.** Real process columns hold
  numbers and prose together -- `90(1000Torr)`, `1->4(0.2sccm)`, `12min30s`,
  `35.5-37.5` -- and Plotly reads such a column as categorical, drawing a
  plausible chart on a nonsense axis. Three strategies are offered per column:
  strict, leading number, and range midpoint. Each shows what it turns the
  non-numeric values into and how many become blank, before it is applied. None
  is the default, because `1->4` says the flow was *ramped* and deciding it "is"
  1 interprets an experiment rather than parsing a cell.

- **Row filters.** Up to two columns narrowed by value set or numeric range,
  because a logbook sheet holds maintenance entries and unrelated experiments
  beside the runs being plotted, and `px.scatter` has no way to exclude a row.

- **Remembered plot settings, keyed by sheet name.** `data/plot_explorer.json`
  (gitignored, per-installation, never raises on a malformed file, following
  `report_settings.json`). Keyed by sheet rather than globally because sheets in
  one process workbook share very few column names -- one global config would
  blank itself on every sheet switch. Not keyed by path: the same workbook
  exists in several OneDrive folders, and keying by path would mean
  reconfiguring for each copy. A remembered column the sheet no longer has comes
  back unset rather than raising.

- **PNG and HTML export** of the plot, via the existing `export_figure_png` /
  `export_figure_html` and the native Save-As dialog.

- **Every control below the sheet picker carries an explicit, sheet-scoped
  widget key.** Streamlit derives a keyless widget's identity from a hash of its
  label, options and index, so two sheets with identical column sets produce the
  *same* widget -- `VAHA_SplitTable` and `VB_SplitTable` in the real process
  workbook are byte-identical -- and one sheet's axis could carry onto the
  other's data. Keying by sheet name makes switching sheets build new widgets
  unconditionally. Note this is a defensive fix: `streamlit.testing.v1.AppTest`
  re-runs the script in-process and does not model the browser's widget-identity
  cache, so the regression tests in `test_plot_explorer_flow.py::TestSwitchingSheets`
  guard the reset/reload logic but pass with or without the keys.

- **The page-render smoke test no longer touches user data.** Rendering
  `pages/5_Plot_Explorer.py` restores the last-used workbook, so
  `tests/integration/test_pages_render.py` was reading the real
  `data/plot_explorer.json`, opening whatever file it named -- a 17-sheet
  workbook on OneDrive -- parsing every sheet, and writing the file back. An
  autouse fixture now redirects the settings path to `tmp_path`. That one test
  went from 6.6 s to 2.3 s, and the suite no longer depends on a machine-specific
  file outside the repo or mutates preferences as a side effect.

- `core.io.folder_picker.prompt_open_path()` -- a single-file open dialog,
  alongside the existing folder picker. `prompt_folder_path` now shares its
  subprocess plumbing; its behaviour is unchanged.

- **statsmodels** is now a dependency (`requirements.txt`), required by
  `trendline`. Only `ols` and `lowess` are offered: `rolling`, `expanding` and
  `ewm` need a `trendline_options` window this page does not expose, and a
  control that raises when used is worse than no control.

### Changed

- **The sidebar navigation is a flat list of five pages.** The single
  `"Raman & PL"` group is gone. It stopped being true at v4.0.0, when the QC
  Panel grew an OM image and Material Presets grew an optical block, and any
  technique-based label goes the same way as techniques are added. No page moved
  or was renamed; only the section heading above them disappeared.

- `export_figure_html()` gained a `self_contained` parameter. False by default,
  so the one existing caller is untouched; True embeds plotly.js (~3 MB larger)
  so the file opens with no internet, which the Plot Explorer's export defaults
  to. The function's docstring had claimed the output was self-contained since
  it was written, while the code used a CDN -- the code was the honest half, and
  the docstring now says so.

## [4.4.0] - 2026-09-15

### Added

- **Optical segmentation can threshold on a fixed contrast instead of `nsigma`.**
  `analyse_frame(..., abs_threshold=...)` takes either a scalar percent or a
  `(below, above)` pair, and the preset carries it as `abs_threshold_below` /
  `abs_threshold_above` on `OpticalParams`. Unset -- the default -- leaves the
  `nsigma` path byte-for-byte as it was, which is what keeps the locked numbers
  in `tests/unit/test_om_contrast.py` meaningful.

  The reason is a feedback trap in `classify()`. Its threshold is
  `mode +- nsigma * min(sigma_l, sigma_r)`, and `min()` was chosen because a
  domain population grows a shoulder that inflates *its own* half-width. That
  defence assumes only one side is contaminated. A film whose domains are small
  and pervasive rather than few and large widens **both** halves equally, the
  minimum stops being a noise width, and the threshold it sets climbs above a
  full layer step -- so the population hides itself. HADH51 is the worked
  example: nine frames whose `sigma_l` and `sigma_r` agree to twelve decimal
  places, 4 sigma landing at +7.1 % against a ~5 % layer step, and 0.14 % of a
  trilayer-bearing film reported as "Above 2L". Stated as a contrast, the
  threshold cannot be moved by the thing it measures.

  The pair is asymmetric on purpose. 2L->3L is one layer step up, but
  2L->substrate can be two or more steps down, so the natural boundaries across
  the HA 202609 set sit near +4 % and -6 % and are not mirror images. Cutting
  symmetrically puts the low threshold inside the film's own noise and inflates
  the "Below" class.

- **`WSe2-HA` material preset**, carrying `abs_threshold_below` 6.0 and
  `abs_threshold_above` 4.25 on its `2L` optical block. A separate material
  rather than a change to `WSe2`, because the pair is calibrated for the HA
  tool's noisier frames and measurably degrades the TSM260803 reference: its
  "Above 2L" falls 3.60 % -> 1.66 % and the class contrast rises +5.44 % ->
  +7.17 %, i.e. back above one layer step. TSM260803's noise sigma is 0.65 % of
  the green mode, so its natural 4-sigma cut is +2.6 %; a fixed +4.25 % clips
  its tail. `WSe2` is unchanged and still runs `nsigma=4`.

### Notes

- A fixed contrast threshold is only meaningful when it clears the frame noise.
  Across the HA 202609 set, 8 of 47 samples have a green-mode noise sigma of
  3.2-8.1 %, which puts a +4.25 % cut at 0.5-1.3 sigma -- inside the bilayer
  distribution. Those frames cannot be segmented at any threshold and need
  re-imaging; under `nsigma` they read ~0 % trilayer and under a fixed contrast
  8-31 %, and neither number is real. Check the threshold-to-sigma ratio before
  trusting a coverage figure.

## [4.3.0] - 2026-09-14

### Added

- **The QC Panel saves its numbers, not just its pictures.** One Save dialog now
  writes four CSVs beside the three PNGs, off the same chosen stem: `_OM_stats`
  and `_Raman_stats` hold the per-class and per-peak mean +/- std the figures
  summarise, `_OM_points` and `_Raman_points` hold the rows those averages were
  taken over -- one per segmented frame, one per fitted peak per grid position.

  The point of shipping both halves is that they agree: averaging a column of a
  `_points` file lands on the number in the matching `_stats` file. Keeping that
  true is why the Raman detail table holds the fits that survived the
  R-squared gate rather than every fit attempted -- the gate's survivors are
  what the figure and the statistics were built from, and a detail table with
  extra rows in it would quietly average to a different answer. The excluded
  count is still reported on screen.

  Both tables are built during the run, from the very `FrameResult` list and
  `(point, FitResult)` pairs the figures were drawn from, and held in session
  state next to the PNGs. A CSV saved beside an image therefore cannot describe
  a different segmentation or a different set of fits than the image it sits
  next to, and a preset edit that invalidates one technique's figure drops that
  technique's CSVs with it.

  New: `modules/optical/io/frame_csv.py` (`export_frame_stats_csv`,
  `export_frame_points_csv`) and two additions to
  `modules/spectra/io/results_csv.py` (`export_point_fits_csv`,
  `export_peak_stats_csv`, the latter taking the `PeakStat` list the report
  tables already use). `contrast.contrast_summary()` joins `class_summary()`,
  both now sharing one ddof rule.

  No PL pair is written. This page fits Raman only -- it calls
  `run_sample_batch(..., pl_preset=None)` -- so no PL measurement exists here to
  tabulate, and the page now says so where the files are listed rather than
  leaving the absence to be noticed. The Sample Report page is where both
  techniques are fitted and written out, to one `.xlsx`.

### Changed

- **QC Panel: "Save Images" is now "Save Results".** The button reads
  "Save Images & Data As...". Same one dialog, same stem-plus-suffix naming, same
  pre-filled `<sample>_QC.png`; the extension the dialog collects is used for
  the images and ignored for the CSVs.

- **CSVs are written as UTF-8 with a BOM.** Excel reads a bare UTF-8 CSV as the
  system codepage and mangles any non-ASCII peak label; the BOM is what stops
  that. Applies to the files this page writes to disk, not to the download
  buttons elsewhere in the app.

## [4.1.0] - 2026-09-11

### Added

- **"FWHM (v1)" comparison column.** `FittedPeak` now also carries
  `width_fwhm_v1` — `2.355 x sigma`, the Gaussian-only width the app reported
  before v3.4.0, computed alongside the correct Voigt width at fit time. The
  Spectra page's Fit Results table always shows it next to `FWHM`, for
  comparing a fit against how it would have been reported pre-v3.4.0. It is
  never the value any other calculation reads.
  On the Sample Report page, a new "Include legacy FWHM (v1) column" checkbox
  (off by default) additionally adds it to the generated .pptx's summary
  tables and the .xlsx's per-point and Summary sheets — `PeakStat` gained
  matching `fwhm_v1_mean`/`fwhm_v1_std` fields, aggregated the same way as
  `fwhm_mean`/`fwhm_std`. The "Raw" row (PL's unfitted empirical stats) has no
  Voigt fit to compute it from, so it's always dashed out. Every reporting
  surface's default (correct) `FWHM` column is unaffected either way.

## [4.0.5] - 2026-09-11

### Changed

- **Image 1's panel gaps are now pixel-exact.** The previous tightening
  (v4.0.4) only reduced the raw/analyzed `wspace` fraction, and a `wspace` is
  relative to the column it divides -- shrinking the fraction only slightly
  shrank the pixel gap, since the nested pair's columns are wider than the
  top-level grid's. `_PAIR_WSPACE` and the new `_POSITION_WSPACE` are now
  back-solved from this module's fixed `figsize` width and `dpi=160` to land
  on exactly 10 px between one position's raw and analyzed panels and 40 px
  between one position and the next -- verified by rendering and measuring
  pixel columns directly, at both 3 and 9 positions. Both figures assume a
  panel near the ~4:3 aspect a camera frame crops to; a frame letterboxed
  inside its panel widens the visible gap beyond these figures, since the
  fraction targets the panel box, not the pixels drawn inside it.

## [4.0.4] - 2026-09-11

### Changed

- **Tighter raw/analyzed pairing in Image 1.** Each position's raw and
  analyzed panels sat exactly as far apart as one position sits from the
  next, because both gaps were the same top-level GridSpec `wspace`. The pair
  now sits on its own nested GridSpec with a smaller `wspace`, so the two
  panels read as a pair and the gap between positions still reads as a
  separator.

## [4.0.3] - 2026-09-11

### Changed

- **OM panel labelling.** Image 1's Original panel used to name the frame's
  detected aperture shape — "P1 (rectangular)" or "P1 (circular)" — which read
  as a claim about the photo rather than what it actually was: the raw,
  unsegmented frame. It now reads "P1 (raw)" for every panel regardless of
  aperture shape; `FrameResult.frame_type` itself is unchanged; only this
  display label moved. The overlay panel's coverage line now reads
  "Analyzed: 2.0 % / 93.9 % / 4.1 %" rather than the bare percentages.

## [4.0.2] - 2026-09-11

### Fixed

- **The OM panels no longer carry a dark grey border.** `mask_margin` excludes
  an outer band of each frame from segmentation, and the QC Panel's Image 1
  showed that band dimmed rather than dropped, so every one of the eighteen
  Original/overlay panels displayed a thick grey frame around a smaller live
  image. `build_om_grid_figure` now crops each panel to the bounding box of
  its `valid` mask before drawing, so a rectangular frame's excluded margin is
  gone entirely. A circular frame's `valid` is an eroded disc, so its bounding
  box still has invalid corners; those are still dimmed, just over a much
  smaller area than before.

## [4.0.1] - 2026-09-11

### Fixed

- **A bad fit is a bad fit, not a crash.** R-squared is `1 - SS_res/SS_tot`,
  which is unbounded below: any model fitting worse than a horizontal line
  through the mean scores negative. `FitResult` validated it into `[0, 1]` and
  raised, so the ordinary result of running a preset against the wrong material
  arrived as `Peak fitting failed: r_squared must be in [0, 1] (got
  -0.1036...)`, an internal invariant surfacing as a user-facing error whose
  suggested remedy — check the peak initial guesses in the preset — pointed away
  from the actual problem. The validation was inconsistent as well: MoS₂'s
  383/408 cm⁻¹ peaks on WSe₂ data collapse to ~zero area and score about -0.11,
  which raised, while the Silicon preset on the *same* data scores +0.00008 and
  passed silently. Both are the same mistake, and both now reach
  `peak_metrics.R_SQUARED_MIN`, the 0.5 quality gate built to drop them.
  Only R-squared > 1 is rejected. Numbers for correctly-matched presets do not
  move; TSM260803 against WSe₂ still fits 225/225 at R² 0.944–0.967.

### Changed

- **The quality gate now says what it did, and keeps saying it.** Spectra
  dropped at `R_SQUARED_MIN` are not fit failures, so they never appeared in
  the "failed to fit" list; they simply left the pipeline and made `n` smaller,
  which reads as a sample with fewer measurements. The QC Panel and the Sample
  Report each report how many were excluded. When *every* spectrum is dropped
  there is no Raman figure either, and the QC Panel now says so in those terms
  and names the selected material as the likeliest cause, rather than leaving a
  bare exclusion count under an empty space where the figure should be. That
  verdict is rendered from persisted state: anything written inside the **Run
  Analysis** block survives exactly one rerun and is wiped by the operator's
  next interaction, which is why the first version of this message was not
  there when it was wanted.
- **`qc_panel_state` derived keys are guarded by a test.** Every key in the
  state dict must be either an operator selection or a member of one of the
  reset tuples. A derived key absent from both outlives the run that produced
  it — the stale-artifact failure the module was written to prevent, and one
  the new verdict would otherwise repeat against the wrong material.

## [4.0.0] - 2026-09-11

Breaking: `data/materials.json` changes shape. A preset is now keyed by
**material alone**, not by material-and-technique, and holds nested `raman`,
`pl` and `optical` blocks. The committed store is migrated in this same change;
a local uncommitted v1 file is migrated on load by a shim that can be deleted
once no one has one.

### Fixed

- **The preset's centre tolerance is honoured.** `fit_voigt_peaks()` re-ran
  `calculate_auto_bounds()` unconditionally, overwriting each peak's
  `center_tolerance` with the mode default of ±5 cm⁻¹. Five of WSe₂'s seven
  peaks were fitted against a tolerance they never asked for; LA, which asks for
  ±10, railed against the ±5 wall it was given and reported 130.011 ± 0.026 — a
  standard deviation of 0.026 across 225 fits being the signature of a peak
  pinned to a bound rather than a peak that was measured. The tolerance now
  travels on `PeakDefinition.center_tolerance` and survives every recalculation.
  This contradicted CLAUDE.md's "the preset owns position and width" and moves
  every WSe₂ number; see **Re-baselined** below.
- **A peak placed outside the spectrum no longer reports a fictional position.**
  Clamping the tolerance window to the data range inverts it when the peak lies
  outside the data entirely — WSe₂'s "center" template sits at 0 cm⁻¹ while the
  same preset crops to x_min=6, which produced `center_min=6.674 >
  center_max=3.000`. lmfit takes an inverted bound without complaint, silently
  **swaps** the two, and fits inside the window that swap invents: the reported
  centre, 6.405 before this change, belonged to neither the preset nor the data.
  `calculate_auto_bounds` now pins such a peak to the nearest edge, and
  `fit_voigt_peaks` expresses that as a fixed parameter rather than a degenerate
  range, which lmfit rejects outright.
- **`Raman_1.txt` is read as Raman by both filename rules.** `sample_scanner`
  accepted `RAMAN` and `RM`; `detect_mode_from_filename` knew only `RM`, so
  VABD38's naming was collected by the scanner and unlabelled by the detector.
  Both now read one shared `RAMAN_PREFIXES` / `PL_PREFIXES` in `parser.py`.
- **A preset can no longer relabel a folder of Raman spectra as PL.** The
  sidebar rewrote *every* loaded file's mode to the selected preset's, Raman
  files included. Technique now comes from each file's own filename.
- **`enabled` is a real control.** `pages/3_Material_Presets.py` hardcoded
  `True` on save, so nothing could write `False` and editing a hand-disabled
  preset silently re-enabled it. It has a checkbox now.

### Added

- **Optical tuning lives in the preset.** `nsigma`, `minpx`, `mask_margin` and
  `ff_divisor` were module constants in `contrast.py`, so the tuning
  docs/OM_Contrast_Algo.md tells an operator to do ("5 if the operator reports
  over-count; 3 if faint domains are missed") meant editing source. They are now
  an `optical` block on the material, **split by layer** — a monolayer film's
  optical contrast against SiO₂/Si differs from a bilayer's, while a Raman or PL
  spectrum does not: the signal says which peaks it has.
- **Two OM images.** The QC Panel produces a clean segmentation grid for a
  report and a diagnostic copy carrying the green-channel histograms for
  internal review, from one segmentation — the ~30 s of analysis happens once
  and only the ~5 s render repeats. Saving writes `_OM`, `_OM_diagnostic` and
  `_Raman` from one dialog. The histograms are what make a saturated frame
  legible *as* one, which is exactly what a customer reading a report does not
  need.
- **Stale figures are cleared per block.** Editing a Raman peak no longer
  discards a 30-second OM segmentation. `preset_staleness` fingerprints the
  `raman` and `optical` blocks separately, and the QC Panel drops only the
  figures whose source block changed.
- **The sidebar says what the filenames said.** Now that technique comes from
  the filename and `detect_mode_from_filename` falls back to "Raman" for a name
  it doesn't recognise, the sidebar shows the mix (`3 Raman, 1 PL, 2 undetected →
  Raman`) and "Run All Files" skips the undetected ones. A guess that nothing
  distinguishes from a reading is worse than no reading.
- **WSe₂ carries a bilayer optical block**, seeded with the algorithm's own
  defaults so it is visible and editable without changing any number. Its
  monolayer block stays absent until it is tuned against VABD38; the QC Panel
  says which it is running.

### Changed

- **`data/materials.json` is v2**, an object with `schema_version` and
  `materials` rather than a bare array — the discriminator is the JSON *type*,
  so a half-migrated file is detected rather than guessed at. `migrate_legacy`
  is a pure function (dicts in, dicts out) and raises rather than guessing on an
  entry carrying both shapes, on a material appearing in both halves, and on a
  duplicate material in the new shape. Unknown `optical` layer keys round-trip
  untouched and are reported by `validate()`: a loader that silently drops part
  of a file turns "I loaded it" into "I edited it".
- **`MaterialPreset` splits into `MaterialPreset` + `TechniquePreset` +
  `OpticalParams`.** `mode` leaves the preset entirely. `OpticalParams` fields
  default to `None` meaning "use `contrast.py`'s default", so the numbers live in
  one place and a material with no optical block produces
  `analyse_frame(**{})` — byte-identical to v3.10.0, which is what keeps
  `tests/unit/test_om_contrast.py`'s locked numbers meaningful.
- **The Material Presets page is one expander per material**, with Raman, PL and
  side-by-side optical layer sections. Layers are stored as `"1L"`/`"2L"` and
  rendered through `contrast.layer_word()`; the stored form is never the word,
  since that helper is one-way presentation and passes unknown values through.
- **The QC Panel's section 3 is "Layer"**, not "Reference Layer", because it now
  selects a tuning block as well as the class labels. Class names are unchanged:
  Below 2L / Bilayer / Above 2L.
- **`contrast.flatfield` takes `ff_divisor`**, plumbed through `analyse` and
  `analyse_frame`. It is a divisor, not a sigma: the blur runs at
  max(H, W) / ff_divisor, so a larger number means a *smaller* sigma.
  `mask_margin` and `ff_divisor` apply to both frame types — whether a frame is
  circular is decided per image at runtime by `is_circular()`, so a preset has no
  way to address one of them, and a name implying otherwise would promise a
  precision that cannot exist.

### Re-baselined

TSM260803, 225 spectra, before → after the centre-tolerance fixes:

| Peak | Centre | FWHM |
| --- | --- | --- |
| E₂g+A₁g | 249.951 → 249.952 | 7.066 → 7.102 |
| 2LA | 260.292 → 260.327 | 5.797 → 5.622 |
| B2g | 308.510 → 308.467 | 4.234 → 4.348 |
| LB | 28.100 → 27.899 | 4.278 → 4.539 |
| LA | **130.011 ± 0.026 → 125.543 ± 0.835** | 36.778 → 36.831 |
| C | 16.620 → 16.385 | 8.283 → 8.853 |
| center | **6.405 → 6.674 (pinned)** | 8.400 → 7.619 |

LA/E₂g+A₁g 0.1503 → 0.1519; B2g/E₂g+A₁g 0.1040 → 0.1031. The schema move itself
changed no fitted value: the post-migration run is bit-identical to the
post-fix one.

### Known issues

- **LA is still cornered, now against the preset's own walls.** 130 of 225 fits
  sit at its ±10 lower bound (125.0), and its Voigt FWHM is railed at 36.83
  against a ceiling of 36.844 — `width_max = 3 × width_fwhm = 45` in σ and γ,
  which is voigt_fwhm(σ_max, γ_max) = 36.844. Both need preset numbers raised,
  which is a decision about the material rather than about the code.
- **TSM260803 remains out of spec on both Raman indicators**: E₂g+A₁g FWHM 7.10
  vs 7.0, defect ratio 0.152 vs 0.13.
- **The deck still shows raw OM frames on slide 1.** The clean image is the
  obvious replacement once it has been used on a few wafers.

## [3.10.0] - 2026-09-11

### Added
- **QC Panel, a fourth section.** Point it at a sample folder, pick the
  reference layer, press Run: it produces an OM layer-segmentation figure and a
  Raman quality figure, and skips either one when the sample has no data for it.
  A sample like `TSM260803` — 50x optical frames and Raman, no PL — produces two
  images and no empty PL placeholder.
- **Optical-microscopy layer segmentation** (`modules/optical/`), a new
  technique module alongside `modules/spectra/`. The algorithm classifies each
  pixel as darker than the film, the film, or brighter, from the green channel's
  own noise width; it is vendored from the `tmd_contrast.py` research script and
  its reasoning is in [docs/OM_Contrast_Algo.md](docs/OM_Contrast_Algo.md).
  Reproduces that script's output on nine real 50x frames to within rounding.
- **Classes are named ordinally** — "Below 2L" / "Bilayer" / "Above 2L" — rather
  than "Substrate" / "Bilayer" / "Multilayer". On a bilayer film, darker than
  the film could be monolayer or bare substrate, and a single frame cannot tell
  them apart; the old naming asserted more than the measurement supports.
- **The OM figure carries a diagnostics row**: the nine green-channel histograms
  with each frame's mode and both thresholds marked. Coverage percentages alone
  cannot show whether a frame segmented sensibly — the predecessor algorithm's
  characteristic failure was every position reading 99 %+ of one class, which in
  an overlay looks like a clean wafer rather than a broken measurement.
- **matplotlib** is now a dependency, used only for these two figures.

### Fixed
- **Multi-spectrum files are fitted instead of silently skipped.** A sample
  folder's `Raman_N.txt` is often a map — one X column plus 25 or 100 intensity
  columns — and the Sample Report parsed it with the two-column
  `parse_spectrum()`, which failed, so every such point was excluded and the
  report's Raman half came out empty. `parse_spectrum_multi()` already existed
  and was simply not wired in. `TSM260803` goes from 0 fitted spectra to 225.
  Documented as Known Issue #4 in docs/Summary.md since v2.x.
- **The whole integration test suite was dead.** Streamlit 1.63 resolves a
  relative `AppTest.from_file` path against the file that calls it rather than
  the working directory, so all 15 integration tests failed with
  `FileNotFoundError` before executing a single page. They now resolve through
  `core.paths.PROJECT_ROOT`.
- **The fitting progress bar no longer freezes** when a file yields more
  spectra than the caller estimated. `sub_callback`'s `totals` is now a floor it
  raises when a label reports more, instead of a fixed denominator that a
  25-spectrum file overshoots 25-fold on its first tick.
- **The progress bar is proportional on multi-spectrum samples.** The stage
  weights were measured on a sample holding one spectrum per point, and fitting
  is the only stage whose cost scales with that count — measured on TSM260803 it
  took 77 % of the run against a declared 21.5 %, so the bar crawled through its
  first fifth and then jumped to done. `stages_for()` now takes `fit_spectra`
  and scales that one weight; `parser.count_spectra()` reads a single row to
  supply it, about 2 ms per file.

### Changed
- **Fit quality is gated and outliers are cut, on every surface.** Fits with
  R-squared at or below 0.5 are dropped, then values outside 1.5x Tukey fences
  *within their own grid position* are excluded from each metric. Cleaning per
  position rather than per sample is deliberate: position-to-position variation
  is the signal the report exists to show, and pooled cleaning would delete it.
  Single-spectrum samples are unaffected — one value per position has no spread
  to judge an outlier against.
- **`aggregate_fit_results()` takes `(point, FitResult)` pairs**, not bare fits,
  since per-position cleaning needs to know the positions.
- **The B2g / E2g+A1g intensity ratio is replaced by C / LB**, reported as the
  "stacking ratio", in the .pptx table, both CSVs and the Excel summary. C and
  LB are the shear and layer-breathing modes — both interlayer vibrations, so
  their ratio speaks to how the two layers sit on each other, which is what a
  bilayer wafer is judged on. This matches the inherited WSe2 analysis, so the
  QC Panel's figure and the report's table cannot disagree.
- **The Sample Report's fitted-spectra grid shows each position's best fit** by
  R-squared. With many spectra per position the previous `dict()` kept whichever
  parsed last, which was arbitrary and silently so.

## [3.9.1] - 2026-09-07

### Fixed
- **Every PNG render crashed under Plotly 7.** `export_figure_png()` asked for
  `to_image(..., engine='kaleido')`; Plotly 6 deprecated that argument and
  Plotly 7 removed it, so the call raised `TypeError: to_image() got an
  unexpected keyword argument 'engine'`, which the wrapper re-raised as
  `RuntimeError: PNG export failed ... Make sure kaleido is installed` — a
  misleading message, since kaleido was installed and working. It took down
  every Sample Report build at the first figure column and the Spectra page's
  Quick Export with it. The argument is simply gone now: Plotly selects kaleido
  on its own when it is installed, on 5.x as well as 7.x.
- **A failed render now chains its cause** (`raise ... from e`), so the
  underlying error keeps its own traceback instead of only surviving as text
  inside the `RuntimeError` message.

## [3.9.0] - 2026-08-24

### Added
- **Saving a Sample Report now writes an Excel workbook of the numbers beside
  the deck.** `💾 Save Report As...` produces `<name>.xlsx` next to
  `<name>.pptx` and its page images — a `Summary` sheet, then a `Raman` and a
  `PL` sheet carrying **one row per fitted peak per point**: center, Intensity,
  FWHM, each one's stderr, shape, R², χ², convergence time, and the source
  file the row came from.

  The .pptx reports one mean ± std over nine points. Anyone asking which point
  was the outlier, or wanting to plot a peak's position across the grid, had to
  refit the sample file by file on the Analysis page and export nine CSVs. The
  workbook is that table, written in the same click as the report.

- **`Summary` mirrors the slide's tables**, built from the very `PeakStat`s the
  .pptx tables are built from (`modules/spectra/io/results_excel.py` takes them
  as an argument rather than recomputing), so the two artifacts written side by
  side cannot disagree about a number. It carries the sample/material/date
  block, each technique's per-peak mean and std, the LA/E2g+A1g and
  B2g/E2g+A1g medians with their MADs, and PL's leading empirical `Raw` row.

- **Mean and std are separate numeric columns**, not one `"248.8 ± 0.2"`
  string, and every cell holds the unrounded value — the number formats only
  decide how many decimals Excel *shows*. A workbook exists so the next person
  can compute with it; a pre-formatted string is a picture of a number.

- **Excluded points are named, not just missing.** A point that failed to fit
  gets a row in the Summary sheet's excluded block with its error. The page has
  always listed them on screen, but a workbook that silently drops nine rows
  reads as a complete record of a sample that was never measured that way.

- Per-point sheets freeze the header row and carry an autofilter, which is how
  you pull one peak's row out of all nine points; a technique that produced no
  fits gets **no sheet at all**, since an empty sheet named `PL` claims a
  technique nobody measured.

### Changed
- **The report's spectra pages now read in the material preset's colors.** The
  peak components on slides 2 and 3 always carried their preset hex
  (`PeakTemplate.color` → `FittedPeak.color` → the plotted line), but they were
  the least visible thing on the slide: drawn thinner than the black total fit
  and under a dense cloud of blue data markers. The components are now the
  heaviest line in the panel, as they already are on the Spectra page, and the
  data is drawn in the color that page draws it.

- **The data trace on every exported figure is the *processed* series' color,
  purple, not the raw file's blue** (`palette.PROCESSED_COLOR`). It always was
  the processed series — `processed_data`, after de-spiking and baseline
  removal, the same numbers the Spectra page shows as "Baseline-corrected" and
  draws purple — so painting it blue made the report disagree with the screen
  about a series they both draw, which is exactly what v3.7.0's shared palette
  was introduced to stop.

  On WSe2 it did more than that: the preset gives `C` and `center` #3276EC, so
  the data and two of the peaks were the same hue and the preset colors stopped
  reading as preset colors. `palette.DATA_COLOR` is now `RAW_COLOR`, named for
  the one layer that uses it — the Spectra page's raw series, which the report
  never draws.

- The Sample Report's save step now reports every file it wrote, the workbook
  included, and the section's caption says what a save will produce.
- `openpyxl>=3.1.0` is now an explicit runtime dependency (it was previously
  only present as a pandas extra). `start.bat` installs it on the next launch.

### Fixed
- **The Spectra page's "Baseline-corrected" layer was purple by luck.** It is
  drawn `mode="markers"`, and its color was set on `line` only — which reaches
  the dots as a Plotly fallback, not as an instruction. It rendered #800080
  because plotly.js defaults a marker's color to its line's; one default away
  from silently becoming a cycled color that no longer matched the report. The
  color is now set on the marker that actually renders, and a test asserts it.

### Notes
- **Intensity in the workbook is the fitted curve's maximum**, via
  `peak_metrics.peak_intensity_and_stderr` — never `FittedPeak.area`. That
  makes it the fifth surface reporting the same quantity under the same name as
  the on-screen table, both CSVs and the .pptx, and a guard test asserts the
  column is an intensity rather than an area (they differ by ~FWHM x 1.064,
  which is the bug v3.3.0 shipped).
- A `Raw` row reports 0 counts for a flat spectrum but leaves its FWHM cell
  **empty**: 0 counts is a measurement, a width with no half-maximum crossing
  is not. Same split the master CSV and the report's Raw row already make.

## [3.8.1] - 2026-08-24

### Fixed
- **The Spectra page paid a 1.5 s image render on every rerun.** The Quick
  Export PNG feeds `st.download_button`, which needs its bytes at render time,
  so the kaleido rasterization ran on every checkbox toggle and file switch
  whether or not anyone ever clicked Download — measured at 1316 ms per rerun.
  It is now memoized: 1510 ms on the first render, 21 ms on every rerun after,
  **71x faster**, and the download button behaves exactly as before.
- **The cache key is the plotly figure itself, hashed by content** (measured
  4.3 ms), not a hand-rolled fingerprint. A fingerprint was written first and
  adversarially reviewed; it had five holes, one of them reachable —
  `st.cache_data` hashes only the decorated function's own source, never its
  callees, so editing `palette.py` moved 25,264 pixels while the digest stayed
  identical and the stale PNG was served until the process restarted. Hashing
  the figure closes that and the other four for free, because every one of
  those inputs is baked into the traces. Tests pin that changed data, a changed
  peak label or colour, changed residuals and a changed palette constant all
  miss the cache.
- **`max_entries=16` and `show_spinner=False`.** The default cache is unbounded
  and each PNG is 165-300 KB, so every refit would add one forever; the default
  spinner would render "Running _export_png_cached(...)" inside the narrow Quick
  Export column. A failing render is not cached, so a broken kaleido install
  still re-pays it every rerun — an error path, not a slow path.
- **"Run All Files" had a progress bar that read one file ahead of reality.**
  It advanced to `(idx + 1) / total` *before* running that file's fit, so with
  two files it showed 50% before any fitting began, and on the last iteration it
  read 100% for the whole of the final — usually slowest — fit before being torn
  down. The fraction is now work actually finished while the label names the
  file currently running, and both live in one `st.progress(text=...)` instead of
  two widgets each carrying half the truth.
- **The batch report no longer vanishes.** `st.rerun()` immediately after the
  loop discarded the success/warning summary and the entire list of failed
  files, so a 12-file batch ended with no record of what happened. It is gone;
  the `show_fit`/`show_components` writes it was there for still take effect,
  because their checkboxes are instantiated further down the same function.
- **The failure list is reachable at all now.** It sat in a collapsed
  `st.expander`, and clicking to open one reruns the script with the button
  False — so the block, and the expander with it, ceased to exist. It renders
  expanded and outside the status (`st.status` is expander-like and Streamlit
  forbids nesting them).
- A batch failure whose message was empty rendered as `**file**:` with nothing
  after it; `.get(k, default)` could not fire because the key is always present.

### Added
- An autouse fixture clearing `st.cache_data` between tests. Streamlit's data
  cache is process-wide and outlives an `AppTest`, surviving across instances and
  across test files in one pytest process — so a test asserting "the PNG has
  bytes" could pass on a payload another test cached, with the render path
  broken.

## [3.8.0] - 2026-08-24

### Added
- **Generate Report now reports progress for the whole build, not just the
  fitting.** A single `st.status` names the stage in flight while a bar tracks
  the measured position through it, so a 25-second build no longer looks like a
  crash.

  The old bar covered only `run_sample_batch`, then called `.empty()` on itself
  and left the remaining ~78% of the wall time completely silent — figure
  rendering, optical-image loading, .pptx assembly and the PowerPoint preview.
  Filling a bar to 100%, deleting it, and then working for another twenty
  seconds is a worse signal than showing nothing at all.

- **The stage weights are measured, not guessed** (`core/report/progress.py`).
  Profiled on a real 9-point sample (`Example/HADG06`: 9 Raman + 9 PL
  2000-point spectra, 9x 2240x1680 BMP images), total 24.5 s:

  | Stage | Time | Share |
  | --- | --- | --- |
  | Fitting spectra | 5.28 s | 21.5% |
  | Rendering Raman figures | 3.98 s | 16.2% |
  | Rendering PL figures | 4.66 s | 19.0% |
  | Loading optical images | 5.37 s | 21.9% |
  | Assembling the report | 2.09 s | 8.5% |
  | Rendering preview in PowerPoint | 3.17 s | 12.9% |

  Equal weights would put the bar at 50% with 78% of the time still to run —
  the same lie in a different shape. Aggregation is excluded deliberately: at
  4 ms a step for it would only flicker.

- **The bar keeps moving through the long stages.** Fitting reports per point
  (18 updates) off the callback `run_sample_batch` already had; each figure
  column and each optical image reports as it completes. 43 updates across the
  build, with the longest motionless stretch 3.17 s — the PowerPoint preview,
  which is one opaque call and is now labelled as such, with the status spinner
  animating throughout.

- **Stages absent from a run are dropped and the rest renormalize.** A
  Raman-only sample does not reserve 19% of the bar for PL figures it will
  never render, and an images-only folder skips fitting entirely instead of
  raising.

### Fixed
- **The fitting stage would have sat still through the entire second
  technique.** `run_sample_batch` fits Raman then PL, restarting its count for
  each, so Raman's 9/9 filled the stage and PL's 1/9 computed a lower fraction
  that the monotonic guard then pinned in place — the bar frozen for 2.9 s of a
  5.3 s stage. The adapter now sums against the combined total, so all 18
  points advance it. Caught by replaying the page's real call sequence against
  the measured timings rather than by reading the code.
- **A build that fails mid-way no longer leaves the status spinning forever.**
  The `with st.status(...)` form resolves to `error` on the way out; a bare
  handle leaves it at `running`, which is indistinguishable from the hang the
  progress exists to rule out. An integration test asserts the errored state.
- **The failed-points list is no longer trapped inside the collapsed status.**
  The status collapses itself on completion, which is no place for the list of
  points that were excluded from the report.

## [3.7.1] - 2026-08-24

### Fixed
- **Clicking the launcher while an older NexAnalyzer was still running could
  serve either version, at random.** `start.bat` pulls the new code, then starts
  a server — but Streamlit does not reload modules an existing server already
  imported, and on Windows a second Streamlit binds the same port *without
  error*. Both servers then listen on 8501 and incoming requests are split
  between them unpredictably: measured directly, three requests to 8501 were
  answered by both PIDs. The browser could show the new version, the old one, or
  flip between them on refresh, and a stale server is also what raises
  `ImportError` on a renamed symbol.
- **The launcher now frees the port before starting.** It finds whatever is
  listening on 8501, and:
  - if it is a Python/Streamlit process, explains that it is running the old
    version and offers to stop it — defaulting to yes after 15 seconds, so the
    double-click path resolves correctly on its own;
  - if the answer is no, it does **not** start a second server, since that is the
    broken state; it points at the running copy and says it may be older;
  - if the owner is not a Python process, it refuses to touch it and suggests
    another port;
  - after stopping, it waits for the port to actually be released before
    launching, and gives up with instructions rather than starting into a
    contested port.
- The port is defined once as `APP_PORT` and passed to `streamlit run`
  explicitly, so the check, the URL printed to the user, and the server can no
  longer disagree.

## [3.7.0] - 2026-08-24

### Added
- **The Sample Report's PL table now leads with the empirical measurement.** A
  "Raw" row carrying center, Intensity and FWHM — read straight off each
  processed spectrum's tallest point, no fit involved — sits above the fitted
  peaks, as mean ± std across the sample's points like every other row. The
  on-screen Fit Results table and the master CSV already showed a "Raw" row for
  PL; the .pptx was the one surface missing it, and now all three agree.
  `peak_metrics.aggregate_raw_peak_stats()` does the aggregation, returning a
  `PeakStat` labelled "Raw" so the existing table renderer needed no new
  plumbing.
- Measured off `processed_data` — after de-spiking and baseline correction, the
  same layer the fit sees — so the empirical intensity is directly comparable to
  the fitted intensities below it rather than being inflated by a baseline
  offset. On a synthetic 9-point sample the two agree to well under a percent,
  which is what makes the row a useful check on the fit.

### Fixed
- **The Sample Report's spectra didn't look like the spectra on screen.** The two
  plotters each picked their own colors, so a fit drawn black and dashed over
  blue points on the Spectra page came out as a solid orange line over
  muted-blue points in the .pptx, and components swapped dashed for solid. The
  report now draws what the screen draws: blue data points, a black dashed total
  fit, solid semi-transparent components in their preset colors, green
  residuals.
- **The colors live in one place, `modules/spectra/viz/palette.py`**, imported by
  both plotters, because two independent definitions is how they drifted apart.
  Only the traces both surfaces draw are shared; the Spectra page's own layers
  (de-spiked, baseline-corrected, live previews) stay its own. A test asserts
  neither plotter hardcodes a shared trace color again, and that both agree
  trace by trace.
- Colors are hex rather than CSS names, because the .pptx legend parses them
  with `_hex_to_rgb`, which falls back to black for anything unreadable — a
  `"blue"` there would have plotted in blue and drawn a black swatch beside it.
- Marker and line *weights* still differ deliberately: a panel shrunk into a 3x3
  grid needs heavier strokes than the full-width on-screen plot, or it reads as
  blank on a projector. Only color and dash are shared.
- Y-axis unchanged: each panel is still normalized to its own tallest peak, which
  is what keeps the nine points comparable on one shared axis.

### Changed
- **A table carrying the empirical row is no longer captioned a "fit summary".**
  The PL table now reads `PL summary (empirical + fitted, mean ± std)`; Raman,
  which has no such row, keeps `Raman fit summary (...)`. The renderer decides
  from the rows it is handed, so the caption cannot drift from the contents.
  `RAW_STAT_LABEL` moved to `core/report/models.py` alongside `PeakStat` to make
  that possible without `core` importing from `modules` — the one rule.
- **`PeakStat.fwhm_mean` / `fwhm_std` are now `Optional[float]`**, and the report
  renders "—" when they are None. A flat or non-positive spectrum has no
  half-maximum crossing, so its empirical width genuinely cannot be measured;
  printing "0.0 ± 0.0" there would read as a measurement. A width is also
  withheld when only some of the sample's points could be measured, since
  averaging that subset while `n` reports the full count would describe a width
  the sample never had. Fitted peaks always carry a width, so their rows are
  unaffected.

## [3.6.0] - 2026-08-23

### Changed
- **One name per quantity, everywhere: `intensity` for the peak's maximum,
  `area` for the integral.** "Amplitude" is gone from the codebase and from
  every surface, because it was the one word that had meant both. The fitted
  curve's maximum — the number a spectroscopist reads off a plot — is
  **intensity**; the area under the peak, which is what lmfit solves for and
  what lmfit itself calls "amplitude", is **area**. `amplitude` now appears
  only where lmfit's own parameter is addressed by name.

  | Old | New |
  | --- | --- |
  | `peak_height_and_stderr()`, `peak_height()` | `peak_intensity_and_stderr()`, `peak_intensity()` |
  | `compute_peak_height_ratio()` | `compute_peak_intensity_ratio()` |
  | `PeakStat.height_mean` / `height_std` | `PeakStat.intensity_mean` / `intensity_std` |
  | `PeakDefinition.height_max` | `PeakDefinition.intensity_max` |
  | `PeakDefinition.amplitude` | `PeakDefinition.intensity` |
  | CSV columns `Amplitude`, `Amplitude_Stderr` | `Intensity`, `Intensity_Stderr` |
  | Sample Report table heading `Amplitude` | `Intensity` |

  The on-screen Fit Results table already said "Intensity" and is unchanged,
  as are `FittedPeak.area` / `area_stderr` and `RawPeakStats.intensity`.
- No numbers change: intensities, widths and the LA/E2g+A1g and B2g/E2g+A1g
  ratios are identical either side of the rename. Only labels and identifiers
  moved.

### Breaking
- **The fit-params and master CSVs now head that column `Intensity` /
  `Intensity_Stderr`.** Anything downstream reading `Amplitude` by name needs
  updating; the values in the column are the same as before.
- **`PeakDefinition`'s serialized keys `amplitude` and `height_max` are now
  `intensity` and `intensity_max`**, and `from_dict()` has no shim for the old
  spelling. In practice nothing in the app writes them: project save/load is not
  reachable from the UI, and the shared `data/materials.json` stores
  `PeakTemplate` rows, which carry neither key — so **material presets are
  unaffected and need no migration**. Only code calling the model API directly is
  affected.

### Documentation
- **`CLAUDE.md` added**, carrying the intensity/area rule, the lmfit caveat, and
  the handful of invariants that are easy to violate and expensive to get wrong.
  The rule previously lived only in a module docstring.
- **`Fitting_Algo.md` §2 documented a bug as current behaviour.** Its "Extract
  Fitted Parameters" listing still showed `width_fwhm_fit = 2.355 * sigma_fit`,
  the Gaussian width that v3.4.0 replaced with `voigt_fwhm()`. Corrected, with a
  note on why it changed. §1-§4 were checked against the code; §5-§8 are now
  labelled as history, whose listings quote code as it stood at the time.
- **47 dead `src/...` file links across the two algo docs repointed** to
  `modules/spectra/...` and verified to resolve. Line-number anchors were dropped
  rather than left to rot on the next edit. `Baseline_Algo.md` now says plainly
  that its algorithm content has not been re-verified since v2.9.0.

## [3.5.0] - 2026-08-23

### Added
- **B2g / E2g+A1g alongside LA / E2g+A1g in the Raman fit summary.** The table
  takes a list of ratios rather than a single one, so further pairs are a
  one-line change to `_RAMAN_RATIO_PAIRS`. Any pair whose peaks aren't both
  present in a fit is dropped automatically, so the list stays safe for
  materials that don't have those modes.

### Changed
- **The two summary tables now size themselves from their row counts.** They
  are stacked, and both heights were fixed, so a second ratio row pushed the
  Raman table straight through the PL one. The Raman height is now derived and
  the PL table placed below whatever it needs.
- **Ratio rows are labelled `LA / E2g+A1g`, with the statistic named in the
  caption** — "peaks mean ± std, ratios median ± MAD" — rather than "(median)"
  on each row. The longer labels wrapped inside the Peak column, and a wrapped
  cell doubles its row height, which is what overran the table below even after
  the heights were derived. The Peak column is also wider now.

## [3.4.2] - 2026-08-22

### Changed
- **`PeakDefinition.amplitude_max` is now `height_max`.** It holds
  `5 × max(Y)` — a ceiling in height units — and only becomes an area when
  `fitting.py` multiplies it by FWHM × 1.064 on the way into lmfit. The old
  name read as lmfit's "amplitude", which is an area, so it named the one
  thing it wasn't. The two local conversions are now `area_guess` and
  `area_max` for the same reason. With this, "amplitude" no longer appears
  anywhere in the codebase meaning something other than peak height.
- No numbers change: heights, widths and the LA/E2g+A1g ratio are identical
  either side of the rename.

## [3.4.1] - 2026-08-22

### Changed
- **The integrated quantity is now called `area`.** `FittedPeak.amplitude` and
  `amplitude_stderr` become `FittedPeak.area` and `area_stderr`. "Amplitude"
  now means peak height consistently — in the UI, the CSV export and the
  Sample Report — while the area under the peak, which is what lmfit solves
  for and what lmfit itself calls "amplitude", says so in its name. Reporting
  one under the other's heading is what made the .pptx disagree with the CSV
  in 3.3.0; nothing on the model carries the ambiguous name any more, and
  tests assert that both `FittedPeak.amplitude` and `PeakStat.amplitude_mean`
  stay gone.
- No numbers change: heights, widths and the LA/E2g+A1g ratio are identical
  either side of the rename.

## [3.4.0] - 2026-08-22

### Fixed
- **Reported FWHM was the Gaussian width, not the Voigt width.** `fitting.py`
  computed `width_fwhm = 2.355 * sigma`, ignoring the Lorentzian `gamma`
  entirely, so every width in the app — the Fit Results table, the CSV export
  and the Sample Report — understated the peak actually drawn by 59-108%. On
  VBBA14, E2g+A1g was quoted as 3.88 where its fitted curve is 8.06 wide, and
  LA as 22.14 where it is 36.50. `docs/Fitting_Algo.md` already documented the
  correct Olivero & Longbothum formula; only the implementation was missing it.
  Widths are now verified against the measured half-maximum of the fitted
  component curves, agreeing to within a few tenths of a percent.
- **FWHM uncertainty propagated only sigma's error.** `2.355 * sigma_stderr`
  describes the Gaussian component rather than the width, and sigma and gamma
  trade off strongly against each other (lmfit reports correlations of -0.82 to
  -0.97 here), so each is poorly determined alone while their combination is
  not. The uncertainty now propagates from both parameters and uses lmfit's
  fitted correlation, falling back to quadrature — an upper bound — when the
  covariance is unavailable.

Peak heights, and therefore the LA/E2g+A1g ratio, are unaffected: they come
from the maximum of the component curve, not from any width parameter.

## [3.3.0] - 2026-08-22

### Fixed
- **The Sample Report's "Amplitude" column reported a different quantity from
  every other surface in the app.** The CSV export and the on-screen Fit
  Results table report peak *height*; the .pptx summary table and its
  LA/E2g+A1g ratio reported lmfit's integrated intensity (area = height x FWHM
  x 1.064) under the same heading. Because WSe2's LA mode is ~6x broader than
  E2g+A1g, their area ratio is ~4.3x their height ratio, so a report could
  never be reconciled against the CSV it came from. The report now uses height
  throughout. On VBBA14, E2g+A1g reads 299.6 rather than 3440.9 and the ratio
  0.114 rather than 0.527.

### Changed
- **The peak ratio is now the median of the per-point ratios**, with the median
  absolute deviation as its spread, rather than the mean and standard
  deviation. A ratio of two fitted quantities is where one badly fitted point
  drags a 9-point mean somewhere no measurement supports. The row is labelled
  "(median)" since the peak rows above it are means, and it prints three
  decimals — at ratios around 0.1, two rounded away the variation the row
  exists to show.
- `compute_peak_amplitude_ratio` is now `compute_peak_height_ratio` and returns
  `(median, MAD, n)`; `PeakStat.amplitude_*` is now `PeakStat.height_*`. Both
  renamed rather than redefined so callers fail loudly instead of silently
  reporting a different quantity.

## [3.2.2] - 2026-08-22

### Changed
- **Report columns drop the Y scale and stack completely flush.** Every panel
  is normalized to its own peak at 1.0, so a Y axis repeated the same three
  numbers nine times across a slide. Removing the tick labels, tick marks and
  horizontal grid also removes the only reason the panels needed a gap and the
  figures needed a wide left margin, so the panels now touch and the spectra
  take the width back. The rotated "Normalized intensity" title on the slide
  still says what the vertical axis is.

## [3.2.1] - 2026-08-22

### Changed
- **The three panels of a Sample Report column now stack flush.** The gap
  between them drops to a hairline, and each point's number moves from a title
  band above its panel to a label inside the panel's top-left corner, where it
  costs no height at all. With the tightened figure margins, column gutter and
  grid bounds, each spectrum gets **16% more height and 20% more area** than in
  3.2.0 — the nine panels read as three continuous stacks rather than nine
  boxes.

## [3.2.0] - 2026-08-22

### Changed
- **Sample Report grids are now three columns, not nine cells.** Each column
  (points 1/4/7, 2/5/8, 3/6/9) is a single figure whose three panels share one
  X-axis, so only the bottom panel carries tick labels. A column is one
  vertical line across the wafer and now reads as one measurement, with peaks
  lining up down it; the two rows of tick labels that saves is most of the
  extra height the spectra get.
- **Every panel is normalized to its own tallest peak, which plots at 1.0.**
  Peak shape and position are directly comparable across the wafer. This
  deliberately discards intensity — a weak point and a strong one now reach
  the same height by construction, unlike 3.1.0's shared raw scale. The Y-axis
  title says "Normalized intensity" accordingly.
- `peak_normalization_scale()` divides by the fitted curve's maximum rather
  than the raw maximum: a surviving cosmic ray or the Rayleigh edge routinely
  tops the raw data, and dividing by that would squash the real peaks.

## [3.1.0] - 2026-08-22

### Changed
- **Sample Report, slides 2 and 3: all nine points now share one pair of axes.**
  Each point's spectrum was autoscaled independently, so every point's strongest
  peak filled its own frame and a weak point looked exactly like a strong one —
  the grid showed nine spectra but said nothing about uniformity across the
  wafer. `shared_axis_ranges()` derives one X and Y range covering every point
  (data and fit curve, with 5% headroom on Y), and every cell is drawn on it.
- **One legend per slide instead of nine.** The legend is drawn on the slide as
  PowerPoint shapes above the grid, not rendered into each cell image. Peak
  components now take their color from the peak's Material Preset rather than
  Plotly's automatic cycling, so a peak is the same color in every cell and one
  key describes them all.
- **The axis titles moved to the slide too** — the Y title rotated in the left
  gutter, the X title centered under the grid — so the two labels appear once
  rather than eighteen times.
- **The spectra are substantially larger and legible.** Beyond the space the
  legend and axis titles gave back, the cell text was badly undersized: a
  figure rendered ~460px tall and placed in a 1.9-inch cell puts one figure
  pixel at about a third of a point, so Plotly's defaults were landing near
  3pt on the slide. Compact figures now set their fonts and stroke weights for
  the size they are actually displayed at, and render at 2x scale.

## [3.0.0] - 2026-08-21

Renamed to **NexAnalyzer** and restructured from a single-purpose spectrum fitter into a
platform: a technique-agnostic `core/` plus one module per measurement technique, with today's
Raman/PL code as the first module (`modules/spectra/`). No analysis behavior changed — same
pipeline, same fit results, same report layout.

### Changed
- **Renamed to NexAnalyzer** (`core/version.py` is now the single source of truth for name and
  version; the UI, launchers, and export filenames read from it instead of hardcoding a string
  in five places).
- **App promoted to the repo root.** `SpectralFit/app.py` is now `app.py`, so a clone is
  `git clone && cd nexanalyzer && start.bat` with no nested folder. The launchers' auto-update
  step no longer reaches one directory up for `.git`.
- **`src/` split into `core/` + `modules/spectra/`** along one rule: `core` knows nothing about
  peaks or spectra, and never imports `modules`. Platform pieces that were filed as
  spectroscopy code moved to `core/` — the PPTX builder (`core/report/pptx.py`), slide
  rasterization (`core/report/slides.py`), native dialogs and figure export (`core/io/`),
  width-aware plot rendering (`core/viz/render.py`).
- **Clearer module names**: `visualization/plotter.py` → `modules/spectra/viz/fit_plot.py`
  (static figures for export/reports), `visualization/unified_plot.py` →
  `modules/spectra/viz/live_plot.py` (the interactive session-state plot),
  `processing/peak_stats.py` → `processing/peak_metrics.py`.
- **Runtime data moved out of the package tree** to `data/` — `materials.json` is committed and
  shared, `report_settings.json` is per-installation and gitignored. Paths resolve through
  `core/paths.py` instead of counting `parent.parent` hops.
- **Pages renamed and reordered** for navigation: Spectra, Sample Report, Material Presets.
- **Sample Report**: the LA/E2g+A1g amplitude ratio is now a bolded final row of the Raman
  fit-summary table instead of a separate text line below it, and the per-point fitted-spectrum
  grids no longer include the residuals strip (unreadable at grid-cell size, and it stole
  height from the spectrum). `plot_composite()` gained `show_residuals`.
- Added `LICENSE` (proprietary, Nexstrom internal) and a root `.gitignore` covering caches,
  local Claude settings, and per-installation data.

### Removed
- **Project save/load** (`src/io/project_io.py`, `src/models/project.py`, 430 lines with tests).
  Its UI was removed in v2.11.0 and never replaced, leaving the module unreachable.
- **`StylingPreferences`** — written into session state on every launch, never read by any plot
  code, along with `get_styling()`/`update_styling()`/`get_mode()`.
- **`add_x_range_indicators()`** and `plot_composite()`'s `x_range_enabled`/`x_min`/`x_max`
  parameters. Unreachable since v2.2: `execute_auto_workflow()` crops the arrays and then resets
  `x_range_enabled` to False, so the branch could never fire. Also dropped the unused
  `width_preset` parameter.
- Orphaned helpers with no call sites: `estimate_peak_bounds()` (a wrapper around
  `PeakDefinition.calculate_auto_bounds()`), `export_single_spectrum_csv()`,
  `detect_negative_x()`, `estimate_baseline_degree()`, and eight unused imports.

### Fixed
- **One rule, one place.** Peak height (`max` of the component curve, with its stderr rescaled
  from lmfit's integrated amplitude) was implemented three times — in the master CSV, in the
  sidebar's Quick Export, and in the on-screen Fit Results table. The PL "Raw row" measurement
  was implemented twice. Both now live in `modules/spectra/processing/peak_metrics.py`
  (`peak_height_and_stderr()`, `raw_peak_stats()`) and are covered by tests; CSV output is
  unchanged.
- Fit-results CSV building moved out of the UI into `modules/spectra/io/results_csv.py`, so
  `sidebar.py` no longer assembles DataFrames inline.
- `_WIDTH_MAP` had lost its only definition when a neighbouring dead function was removed;
  `render_plot()` now lives with it in `core/viz/render.py`.

### Known limitations
- Sample folders where each point file is itself a multi-spectrum hyperspectral file aren't
  fitted yet — carried over from v2.12.0, unchanged.
- The Sample Report's summary tables and its LA/E2g+A1g ratio report lmfit's *integrated*
  amplitude, while the CSVs and the on-screen table report peak *height*. Both conventions are
  now documented in `peak_metrics.py`, but they are still different numbers under the same
  "Amplitude" label.

## [2.12.0] - 2026-08-21

### Added
- **Sample Report page** (`pages/sample_report.py`): pick a sample folder containing a 9-point OM + Raman + PL measurement grid, fit every Raman/PL file against one material's presets, and generate a three-slide PPTX report — no manual plotting or copy-pasting required.
  - **Slide 1 (overview)**: 3x3 OM image grid (magnification selectable, e.g. `100x`/`10x`) plus Raman and PL fit-summary tables (mean ± std of center/amplitude/FWHM per peak label, across the 9 points). For WSe2 Raman specifically, the Raman table carries an extra bolded row with the LA/E2g+A1g amplitude ratio (`compute_peak_amplitude_ratio()` in `src/processing/peak_stats.py`) — omitted automatically for materials without both peak labels.
  - **Slides 2 & 3**: a 3x3 grid of each point's individually fitted spectrum for Raman and PL respectively, rendered with `plot_composite(show_residuals=False)` — the same data+fit+components view used elsewhere in the app, minus the residuals strip, which is unreadable at grid-cell size and only steals height from the spectrum.
  - Missing content (no image, no fit, no stats — e.g. a technique entirely absent from a sample) renders as an empty black-outlined box rather than an error or a gray "N/A" placeholder, keeping partial reports clean.
  - After generating, the page renders the actual .pptx's slides to on-screen preview images (not a separate approximation of the layout) via PowerPoint COM automation (`src/io/slide_render.py`), and saves them alongside the .pptx as `_page1.png`/`_page2.png`/`_page3.png` when you save.
  - Folder discovery (`src/processing/sample_scanner.py`) matches `RM`/`Raman`/`rm`/`raman` (Raman) and `PL`/`pl` prefixes with either `-` or `_` before the point number (e.g. `RM_1.txt`, `RM-8.txt`, `rm-9.txt` all resolve); files that don't match a recognizable pattern are listed as ignored rather than guessed at. A "default material" selection persists across restarts (`src/presets/report_settings.json`, separate from `materials.json`).
  - New dependencies: `python-pptx`, `Pillow`, and (Windows-only, via a `sys_platform` marker) `pywin32` for the PowerPoint COM automation.
- New `tests/integration/test_sample_report_flow.py` drives the actual page via `streamlit.testing.v1.AppTest`, closing the coverage gap Summary.md previously flagged as "not practically unit-testable" for UI-workflow integration.

### Known limitations
- Sample folders where each point file is itself a multi-spectrum hyperspectral file (e.g. ~100 sub-acquisitions per grid point, seen in some real customer QC data) aren't fitted yet — those files currently fail to parse per point and are excluded gracefully (shown in an errors panel) rather than averaged or fit individually. Deferred; `parse_spectrum_multi()` in `src/processing/parser.py` is the building block for when this is picked back up.

## [2.11.0] - 2026-08-12

### Added
- **Multi-page app.** `app.py` is now a thin `st.navigation()` entrypoint grouping pages under a "Spectral Fit" section: **Analysis** (`pages/analysis.py`, today's workflow — unchanged in behavior, just relocated out of `app.py`'s top level) and **Material Presets** (`pages/material_presets.py`, new). Grouping under an explicit section means a future page (e.g. an OM Analyzer) can be added as its own sibling section without reworking these two.
- **Material Presets page**: a full in-app editor (create/edit/delete) for the materials used by Run Auto-Workflow / Run All Files — despike threshold, baseline algorithm + parameters, X-range, exclusion ranges, and peak templates (editable as a table via `st.data_editor`, add/remove rows freely). Replaces hand-editing an Excel file.
- `src/io/preset_store.py`: JSON load/save for `src/presets/materials.json`, the new preset store (replaces `src/io/preset_parser.py`'s Excel parsing).

### Changed
- **Material presets are now embedded in the app, not loaded from an Excel file.** The sidebar's Material Presets section is now just a "Select Material" dropdown reading live from `src/presets/materials.json` — the Browse Preset File / Reload Presets / clear (✖️) buttons and the Excel file-path caption are gone. Add or edit materials on the new Material Presets page instead.
- **View Options moved to the very bottom of the sidebar** (after Loaded Files), instead of sitting between Batch Export and Reset to Raw.
- The 4 existing presets (WSe2_PL, WSe2_Raman, MoS2_Raman, Silicon_Raman) were migrated as-is into `src/presets/materials.json`.

### Removed
- **`presets/` folder removed**: `material_presets.xlsx`, `create_template.py`, `README.md`. **`src/io/preset_parser.py`** (Excel parsing) and its tests (`tests/unit/test_preset_parser.py`) removed along with it; `tests/conftest.py`'s now-unused `tmp_preset_xlsx` fixture removed too.
- **`PeakTemplate.amplitude` field dropped.** Verified dead: `src/processing/fitting.py` auto-estimates amplitude from the actual spectrum data at fit time and never consults the preset's value (this was already documented on `PeakDefinition.amplitude`). `to_peak_definition()` now passes a fixed placeholder instead.
- **`MaterialPreset.to_processing_settings()` removed** — zero call sites anywhere in `src/` or `tests/`; dead code.
- **`PresetLibrary` class removed** from `src/models/preset.py`. It existed to wrap Excel's sheet-name-based lookup (`get_preset()` parsed a `"Material_Mode"` string back into two fields via `parse_sheet_name()`); JSON presets already have `material_name`/`mode` as separate fields, so callers now use a plain `dict[(material_name, mode), MaterialPreset]` directly — no parsing round-trip, no wrapper class. `PresetLibrary.last_loaded` (set on construction, never read anywhere) is gone with it.
- `validate_preset_schema()` and `parse_sheet_name()` (both Excel-specific, in the deleted `preset_parser.py`) — superseded by `MaterialPreset.validate()`, reused directly by the new editor's save action. `parse_exclusion_ranges()` was *not* dead (still used by `auto_workflow.py` for the exclusion-ranges feature) — it moved to `src/models/preset.py` instead of being deleted, with its pandas `NaN` check simplified since JSON never produces one.
- `get_sheet_count()` — repurposed as a "N material(s) configured" caption on the new Material Presets page rather than deleted outright.

## [2.10.0] - 2026-08-12

### Removed
- **Project save/load removed.** The sidebar's "Project" section (Save Project button and the "Load Project" `st.file_uploader`, including its `_loaded_project_file_id` re-run guard) is gone from `src/ui/sidebar.py`. `src/io/project_io.py` (`save_project()`/`load_project()`) is untouched and still covered by `tests/unit/test_project_io.py` — only the sidebar UI call sites were removed.
- **Plot preview removed from Export.** The composite plot no longer renders on screen before download. `plot_composite()` is still built internally so PNG/HTML Quick Export keeps working — it's just never passed to `render_plot()`.
- **Right-hand control panel removed.** `src/ui/control_panel/` (View Options, Export, Reset to Raw) is deleted; `app.py` no longer splits into `col_center`/`col_right` — the plot now takes the full width next to the sidebar.

### Changed
- **Quick Export, Batch Export, View Options, and Reset to Raw moved into the sidebar** (`src/ui/sidebar.py`), placed right after the Material Presets section (below the Run Auto-Workflow / Run All Files buttons), so the whole workflow — presets, run, export, view/reset, load/manage files — lives in one place. The pre-fit placeholder shortened to "Run Auto-Workflow to enable export." since it now sits directly under those buttons.
- "Load Spectra" (Browse Spectrum Files) and "Loaded Files" (current-file info, Remove File / Delete All) are unchanged and remain in the sidebar, now below the export/view/reset block.

## [2.9.0] - 2026-08-12

### Removed
- **Manual step-by-step processing UI removed.** The accordion's Processing Range, De-spiking, Baseline Correction, and Peak Fitting sections (`src/ui/control_panel/processing_range.py`, `despike.py`, `baseline.py`, `peak_fit.py`, `shared.py`) are gone. Processing a spectrum is now done exclusively through the sidebar's Material Preset **Run Auto-Workflow** / **Run All Files** buttons (`execute_auto_workflow()` in `src/processing/auto_workflow.py`), which already existed and needed no changes. The control panel now only shows View Options, Export, and Reset to Raw.
- **Export section's "Advanced Options" (detailed per-point CSV) dropped.** `export_single_spectrum_csv()` itself is untouched in `src/io/export.py` (and still covered by `tests/unit/test_export.py`) — only its UI call site was removed. Quick Export (PNG/HTML/CSV fit parameters) and Batch Export (master CSV across files) are unchanged.

### Changed
- The Export section is no longer step "5️⃣" of an accordion — `render_export_section()` lost its `is_expanded` parameter and outer `st.expander(...)` wrapper, since it's now the panel's only content.
- Sidebar now expands by default (`initial_sidebar_state="expanded"`) since it's the only place processing can be started from.
- `tests/unit/test_control_panel_baseline.py` removed (tested the deleted `control_panel/baseline.py` UI module; `tests/unit/test_baseline.py`, which tests the underlying `src/processing/baseline.py` algorithms used by `auto_workflow.py`, is unaffected).
- `USER_GUIDE.md`, `README.md`, `Summary.md` updated to describe the preset/auto-workflow-only flow; the now-inapplicable "Using SpectralFit (Manual Workflow)" section was removed from `USER_GUIDE.md`.

## [2.8.0] - 2026-08-12

A maintainability and correctness pass: no user-facing features were added, but several real bugs were fixed (including two that could crash or hang the app), the codebase gained its first automated test suite, and the largest UI module was split apart for maintainability.

### Fixed
- **"Load Project" crashed on every use** (`src/ui/sidebar.py`): `load_project()` returns a `(files, plot_width_preset)` tuple, but the call site assigned the whole tuple to `st.session_state["files"]` without unpacking it, so the plot immediately crashed with `AttributeError: 'tuple' object has no attribute 'keys'`.
- **Fixing the above exposed an infinite-rerun loop**: `st.file_uploader`'s value stays truthy across reruns until the file is removed or replaced. The handler had no guard, so it re-processed the same upload — including its own `st.rerun()` — on every rerun, forever, and the app never rendered past the sidebar. Fixed by tracking the uploaded file's stable `.file_id` and only processing it once.
- **Whitespace-delimited spectrum files were completely broken** (`src/processing/parser.py`): the whitespace-delimiter fallback used `pd.read_csv(..., delim_whitespace=True)`, a kwarg removed in the installed pandas version, so it raised `TypeError` on every attempt — silently swallowed by the surrounding delimiter-sniffing loop.
- **Missing spectrum files reported the wrong error**: because of the same swallowed-exception loop, a genuinely missing file surfaced as a generic "File must have at least 2 columns" `ValueError` instead of `FileNotFoundError`. Fixed by checking file existence explicitly before the delimiter loop.
- **Non-functional mobile-detection code removed** (`app.py`, `control_panel/__init__.py`): the injected JavaScript viewport-detection block could never actually communicate back to Python (Streamlit doesn't support that callback), so `is_mobile` was permanently `False` and an entire unreachable mobile-layout code path existed. Removed; the app now has a single (the only reachable) desktop layout.
- **Broken footer links** (`app.py`): "Documentation" pointed at a file deleted in an earlier commit; "Report Issues" pointed at a `your-repo` placeholder URL. Both now point at the real repository.
- **Confusing peak-count logic simplified** (`src/processing/fitting.py`): `auto_find_peaks()`'s peak-selection formula looked like it enforced a `min_peaks` floor but never actually could (Python slicing silently truncates) — simplified to what it actually computes, with output unchanged.

### Added
- **Automated test suite**: `pytest` configured via `pyproject.toml`; 119 unit tests added under `tests/unit/` covering despiking, all 5 baseline algorithms, Voigt fitting, spectrum/preset parsing, CSV/project export and import, and stale-fit detection. Previously the project had zero automated tests.

### Changed
- **`src/ui/control_panel.py` (2,687 lines) split into a package**, `src/ui/control_panel/`, one module per accordion section (`processing_range.py`, `despike.py`, `baseline.py`, `peak_fit.py`, `export.py`) plus `shared.py` for cross-section helpers. The public interface (`render_control_panel()`) is unchanged.
  - Deduplicated the baseline algorithm dispatch, which was previously implemented three times (parameter widgets, live preview, and the real run) with drift risk between preview and applied results — now a single `_run_baseline_algorithm()` helper used by both preview and run paths.
  - Consolidated the repeated `show_raw`/`show_despiked`/`show_corrected`/`show_fit`/`show_components`/`show_residuals` session-state rewrite (previously duplicated near-verbatim across all 5 sections) into a single `_set_view_stage()` helper.
  - `compute_preprocessing_hash()` / `mark_fit_stale_if_needed()` moved to a new `src/utils/fit_staleness.py`, fixing a layering violation where `src/processing/auto_workflow.py` (a processing-layer module) had to import from the UI layer to reach them.
- **Dead code removed**: 6 unused UI modules (`file_panel.py`, `control_panel_old.py`, `export_tab.py`, `fit_tab.py`, `preprocess_tab.py`, `components.py`, ~1,300 lines) plus 3 unreachable functions in `src/visualization/plotter.py` (`plot_preview`, `plot_with_baseline`, `apply_plot_width`) that had no callers anywhere in the repo.
- **Documentation consolidated**: `FITTING_IMPROVEMENTS.md` merged into `Fitting_Algo.md` as a dated implementation-history section (it was a near-duplicate changelog for work already described there); the version-history content that had been triplicated across `README.md`, `Summary.md`, and this file is now only here; `Summary.md` trimmed to focus on architecture/data-model/decisions (its stale project-structure tree and data-model code samples were also corrected to match the current code).

## [2.7.1] - 2026-05-31

### Added
- **Auto-update on launch**: `start.bat` (Windows) and `start.sh` (macOS/Linux) now pull the latest version from GitHub each time they run, so anyone who cloned the repo always launches the newest release. The check runs `git pull --ff-only` from the repo root, reinstalls any changed dependencies, then starts the app.
- **Never blocks**: if Git isn't installed, the copy isn't a git checkout (e.g. a ZIP download), or the network/GitHub is unavailable, the launcher prints a short notice and starts the version you already have.

### Changed
- README install instructions now recommend `git clone` (for auto-updates) with a manual-setup fallback, and note that ZIP downloads don't auto-update.

### Added
- **"Save Master CSV to folder" button** in the Export section's Batch Export block. Opens a native OS Save-As dialog **pre-pointed at the folder the raw `.txt` data was loaded from**, with an **editable filename**, and writes the master CSV directly there — no more browser-Downloads detour. The existing in-browser "Download Master CSV" button is retained as a fallback.
- New `source_dir` field on `SpectrumFile` records the folder each spectrum was loaded from (captured by the Browse picker). Backward-compatible: old project JSON without this field loads fine (defaults to `None`).
- New reusable `prompt_save_path()` helper in `src/io/export.py` wrapping `tkinter.filedialog.asksaveasfilename` in a subprocess (same pattern as the Browse-files dialog).

## [2.6.0] - 2026-05-30

### Added
- **"Delete All Files" button** in the sidebar's "Loaded Files" section. A single click clears every loaded spectrum at once (wired to the existing `clear_all_files()` helper), instead of removing files one by one. Placed side-by-side with the existing "Remove File" button via a two-column layout.

## [2.5.0] - 2026-05-16

### Added
- **Multi-select file picker** for spectrum input: the sidebar now exposes a **"Browse Spectrum Files"** button that opens a native OS multi-select dialog (`tkinter.filedialog.askopenfilenames`), filtered to `.txt` with an "All files" fallback. Ctrl-click / Cmd-click to pick multiple files in one dialog session.
- Last-picked directory is remembered as the next dialog's starting location (session-state key `'last_picked_dir'`).
- Pop-based reload guard via a transient `'pending_files_to_load'` session-state queue — picked files are parsed exactly once on the next rerun; no per-rerun re-parsing.

### Changed
- **Sidebar "Load Spectra" block fully replaced**: the "Folder Path" text input and "Browse File Folder" button are removed. The new picker preserves all downstream behavior (multi-Y `__1`/`__2` splitting, `detect_mode_from_filename` auto-detection, per-file duplicate skipping, per-file error isolation).
- Subprocess output for the new picker is **JSON-serialized** (rather than bare `print()`) so picked paths with spaces, commas, or unicode round-trip safely.
- **PL "Raw" summary row** in the fit-results table is now rendered **at the top** of the table instead of the bottom — applies to both the in-app table ([src/visualization/unified_plot.py](src/visualization/unified_plot.py)) and the exported master CSV ([src/io/export.py](src/io/export.py)). Easier raw-vs-fit comparison.
- Sidebar success message reads `"Loaded N file(s)"` (dropped the "from folder" suffix).

### Removed
- Session-state keys `'last_folder_path'` and `'loaded_folder_path'` (replaced by `'last_picked_dir'` and `'pending_files_to_load'`). These keys were never written to project JSON, so existing saved projects load unchanged.

## [2.4.1] - 2026-02-02

### Changed
- **Removed Display Settings UI** from sidebar - plot width now defaults to Full (100%) everywhere
- **Moved Fit Results table** from right-side control panel to below the spectrum plot in center column
- **Removed "Residuals" subplot title** that overlapped with x-axis labels (y-axis label retained)

### Fixed
- All `plot_width_preset` defaults updated from "Standard" to "Full" across codebase

## [2.3.0] - 2026-01-08

### Added
- **Material Preset System**: Excel-driven, one-click auto-workflow (X-range → Despike → Baseline → Fitting) across a full pipeline. Sheet-per-material design (e.g. "Graphene_Raman", "MoS2_Raman"), auto-discovered from sheet names; mode validation prevents applying a Raman preset to a PL file. No code changes needed to add a new material — see [presets/README.md](presets/README.md) for the Excel schema. Batch-processing 10+ files with identical parameters now takes seconds instead of minutes.

### Changed
- **Auto-Workflow rewritten** to replicate the exact manual step-by-step workflow instead of taking shortcuts. Previously it used `original_data` (instead of `raw_data`) as the X-range source, didn't reset flags or clear previews correctly, and didn't mark fits stale after preprocessing changes. It now updates both `raw_data` and `processed_data`, resets flags, clears previews, marks fits stale, and updates view options at every stage — producing identical results to manual processing.

### Fixed
- **Despike tuple-unpacking bug** in auto-workflow: `remove_spikes()` returns `(y_clean, spike_mask)`, but the whole tuple was being assigned to the Y array, which numpy then coerced into an invalid 2D array. Fixed by unpacking both return values.
- **ALS baseline parameter name mismatch**: auto-workflow called the ALS functions with `lam=` instead of the actual keyword `lambda_=`, silently halting the pipeline at the baseline stage.
- **Sparse matrix format error** ("spsolve requires A be CSC or CSR matrix format"): added `A = A.tocsc()` before all three `spsolve()` calls in `baseline.py`, fixing ALS, Rolling Ball, and airPLS.
- **Preset file not found**: the default preset path was relative and broke depending on the working directory the app was launched from. `get_default_preset_path()` now resolves an absolute path via `Path(__file__).resolve()`.
- **X-range validation crash** ("StreamlitValueBelowMinError"): a saved `x_min` from a preset could be slightly below the actual data minimum (floating-point precision). Added clamping so X-range inputs always stay within the current data's bounds.

## [2.2.1] - 2025-12-23

### Added
- **Real-time preview for baseline correction** - See red dashed baseline preview before applying
- **Real-time preview for de-spiking** - See orange dashed preview of spike removal
- **X-range processing** - Crop spectrum to specific region before processing
- **Improved peak fitting algorithm** with critical fixes:
  - Fixed amplitude initialization (convert peak height to integrated intensity)
  - Shape-aware width initialization using Gaussian/Lorentzian mixing
  - Adaptive parameter bounds (wider tolerance for broader peaks)
  - Improved auto-find FWHM estimation with curvature-based fallback
  - Peak overlap detection with actionable warnings
- **Enhanced UI/UX**:
  - Simplified View Options with organized checkbox groups
  - Auto-managed plot layer visibility at each processing stage
  - Removed left file panel - plot now takes 70% width
  - File navigation dropdown with left/right buttons at top of plot
  - Scrollable control panel (800px height)
  - Reordered workflow sections for better flow
- **Algorithm documentation**:
  - Comprehensive Baseline_Algo.md (algorithm analysis)
  - Comprehensive Fitting_Algo.md (algorithm deep dive)
  - FITTING_IMPROVEMENTS.md (v2.2.1 enhancement summary)

### Changed
- **Plot visibility behavior** (auto-managed):
  - X-range stage: Show only "Raw" curve
  - Despike stage: Show "Raw" AND "De-spiked" for comparison
  - Baseline stage: Show "De-spiked" AND "Preview baseline" (red dashed)
  - Peak fit stage: Show "Corrected", "Fit Total", and optionally "Components"
- **Removed "Preview Corrected" green curve** from baseline preview (user request)
- **UI section order**: Processing Range → De-spiking → Baseline → Peak Fitting → Export → Reset to Raw → View Options
- **Amplitude bounds**: Increased from 2× to 5× max intensity (accounts for sharp peaks)

### Fixed
- **Critical crash fixes**:
  - Peak deletion IndexError when deleting non-consecutive rows (P0)
  - Peak addition TypeError when clicking "+" button (P0)
- **Behavioral fixes**:
  - Reset to Raw now restores original data (before X-range cropping)
  - Plot layers automatically clear when advancing to next processing stage
  - Preview states cleared after fitting runs (no stray preview curves)
- **Parameter fixes**:
  - Despike sensitivity range extended to 30.0 (was 15.0)
- **Fitting algorithm improvements**:
  - Fixed amplitude initialization (critical: lmfit expects integrated intensity, not peak height)
  - Fixed parameter extraction to handle both Parameter objects and floats
  - Fixed component curve evaluation (use kwargs not params dict)
  - Fixed FitResult validation (allow empty peaks when failed)
  - Fixed baseline parameter naming (lambda_ not lam)

### Quality Improvements
- **Expected R² improvement**: 0.85-0.92 → 0.95-0.99 (for well-behaved spectra)
- **Convergence rate improvement**: 60-70% → 90-95%
- **Bound-hitting issues**: Common → Rare
- **Auto-find quality**: Poor → Good

## [2.2.0] - 2025-12-20

### Added
- **Single-page, three-panel layout** (files/plot/controls)
- **X-range cropping** with data masking
- **Real-time preview** for despike and baseline operations
- **Full peak fitting** with Voigt models
- **Sequential workflow** with auto-expand accordion
- **Unified multi-layer plot** visualization
- **Processing Range section** with X-min/X-max controls
- **De-spiking section** with threshold slider
- **Baseline Correction section** with algorithm selection (Polynomial, ALS, Rolling Ball, Spline, airPLS)
- **Peak Fitting section** with auto-find and manual peak management
- **View Options section** with layer visibility controls
- **Status tracking** with progress badges in file cards
- **Stale fit detection** using hash-based preprocessing change tracking

### Changed
- Migrated from multi-tab layout to single-page accordion layout
- Desktop layout: 70% plot width, 30% control panel
- Mobile layout: Stacked vertical (controls → plot)

## [2.1.0] - 2025-12-19

### Added
- Real-time baseline preview with instant parameter feedback
- Auto mode detection from filename patterns (RM*/PL*)
- Plot width control (Compact/Standard/Wide/Full presets)
- Negative Y value support with automatic shifting
- Enhanced export with new metadata columns

## [2.0.0] - 2025-12-18

### Added
- Initial release of SpectralFit v2.0
- Raman and Photoluminescence spectrum analysis
- Cosmic-ray spike removal (modified Z-score)
- Baseline correction (Polynomial, ALS)
- Multi-peak Voigt profile fitting
- Interactive Plotly visualizations
- Batch processing support
- Project save/load (JSON)
- CSV export for fit results

---

## Version History Summary

- **v2.9.0** (2026-08-12): Removed the manual step-by-step processing UI — spectra are now processed exclusively via the sidebar's Material Preset Run Auto-Workflow; the control panel shows only View Options, Export, and Reset
- **v2.8.0** (2026-08-12): Bug-fix and maintainability pass — fixed a crash and an infinite-loop bug in project loading, fixed broken whitespace-delimited file parsing, added a 119-test pytest suite, split `control_panel.py` into a package, removed dead code, consolidated documentation
- **v2.7.1** (2026-05-31): Launchers auto-update from GitHub on each run (with offline/ZIP fallback)
- **v2.7.0** (2026-05-30): "Save Master CSV to folder" — native Save-As dialog writes the master CSV into the raw-data folder with a user-typed filename
- **v2.6.0** (2026-05-30): "Delete All Files" button in the sidebar to clear all loaded spectra at once
- **v2.5.0** (2026-05-16): Multi-select file picker replaces folder picker; PL Raw row moved to top of fit-results table
- **v2.4.1** (2026-02-02): Display Settings removed (plot width defaults to Full); Fit Results moved below plot
- **v2.4.0** (2026-01-XX): Batch auto-workflow ("Run All Files") + smart file navigation
- **v2.3.0** (2026-01-08): Material Preset System (Excel-based auto-workflow)
- **v2.2.1** (2025-12-23): Critical fitting algorithm improvements + UI refinements
- **v2.2.0** (2025-12-20): Single-page accordion layout + real-time previews
- **v2.1.0** (2025-12-19): Real-time baseline preview + auto mode detection
- **v2.0.0** (2025-12-18): Initial release
