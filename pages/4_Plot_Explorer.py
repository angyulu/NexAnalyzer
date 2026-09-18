"""
Plot Explorer: an arbitrary spreadsheet, plotted.

Point it at any .xlsx, pick one sheet, shape the columns, drive
plotly.express.scatter. It knows nothing about peaks, spectra, material
presets or NexAnalyzer's own .xlsx export, and that is deliberate — see
modules/dataviz/__init__.py.

One sheet at a time, never several combined. One plot draws on one tool's runs,
and the sheets in a process workbook are one tool each; a scatter mixing two
tools' chemistries onto one axis implies a comparison that isn't valid. Sheets
are picked, not merged.

The page is four decisions in order — which workbook, which sheet, what the
columns mean, what to draw — and only the last of them is the plot. The three
before it exist because a hand-kept lab notebook arrives with two header rows,
repeated column names, numbers stored as prose and a seventh of its rows blank.
modules/dataviz/io/excel_source.py carries the reasoning for each.
"""

import os

import streamlit as st

from core.io.export import export_figure_html, export_figure_png, prompt_save_path
from core.io.folder_picker import prompt_open_path
from core.viz.render import render_plot
from modules.dataviz.io import config_store
from modules.dataviz.io import excel_source as source
from modules.dataviz.ui.state import get_state, reset_sheet_selections, reset_workbook
from modules.dataviz.viz import scatter

st.title("📈 Plot Explorer")
st.markdown(
    "Plot any Excel sheet. One sheet at a time — pick the workbook, say how the "
    "columns should be read, then draw."
)

state = get_state()

NONE_LABEL = "— none —"

#: The coercion strategies offered per column. "none" is excluded: not listing
#: a column is how you decline to convert it.
STRATEGY_CHOICES = [s for s in source.COERCION_STRATEGIES if s != "none"]


# ------------------------------------------------------------------ caching
# Keyed on the file's mtime as well as its path, so saving an edit in Excel and
# pressing Reload actually re-reads rather than returning the parse from before
# the edit.
@st.cache_data(show_spinner=False)
def _cached_sheets(path: str, mtime: float, header_rows: int):
    return source.list_sheets(path, header_rows=header_rows)


@st.cache_data(show_spinner="Reading sheet…")
def _cached_frame(path: str, mtime: float, sheet: str, header_rows: int):
    return source.read_sheet(path, sheet, header_rows=header_rows)


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _column_select(label: str, columns, current, key: str, help_text: str = None):
    """A dropdown over columns where blank means "unset"."""
    options = [NONE_LABEL] + list(columns)
    index = options.index(current) if current in options else 0
    chosen = st.selectbox(label, options=options, index=index, key=key, help=help_text)
    return None if chosen == NONE_LABEL else chosen


# -------------------------------------------------------------- 1. Workbook
st.subheader("1. Workbook")

if state["path"] is None:
    remembered = config_store.load_last_location().get("path")
    if remembered and os.path.exists(remembered):
        state["path"] = remembered

col_pick, col_reload, col_path = st.columns([1, 1, 3])
with col_pick:
    pick_clicked = st.button("Select Workbook", use_container_width=True)
with col_reload:
    reload_clicked = st.button(
        "Reload", use_container_width=True, disabled=state["path"] is None,
        help="Re-read the file after editing it in Excel.",
    )
with col_path:
    st.caption(state["path"] or "No workbook selected yet.")

if pick_clicked:
    try:
        picked = prompt_open_path(
            default_dir=os.path.dirname(state["path"]) if state["path"] else "",
            title="Select Excel Workbook",
        )
    except Exception as e:
        st.error(f"Failed to open the file browser: {e}")
        picked = None

    if picked:
        state["path"] = picked
        reset_workbook(state)
        st.rerun()

if reload_clicked:
    _cached_sheets.clear()
    _cached_frame.clear()
    st.rerun()

if state["path"] is None:
    st.info("Select an .xlsx workbook to begin. Legacy .xls files are not supported.")
    st.stop()

if not os.path.exists(state["path"]):
    st.error(f"The workbook is no longer at {state['path']}. Select it again.")
    st.stop()

# The header-row count belongs with the workbook rather than the sheet: it is a
# property of how the file was written, and every sheet in one of these
# workbooks is laid out the same way.
state["header_rows"] = st.number_input(
    "Header rows",
    min_value=1, max_value=5, value=int(state.get("header_rows", 1)), step=1,
    key=f"pe::book::{state['path']}::header_rows",
    help=(
        "How many rows at the top name the columns. Set 2 where row 1 is the name "
        "and row 2 is the unit — they are joined into 'H2O (torr)', which is also "
        "what separates three columns all called 'H2O'."
    ),
)

try:
    sheets = _cached_sheets(state["path"], _mtime(state["path"]), state["header_rows"])
except Exception as e:
    st.error(f"Could not read the workbook: {e}")
    st.stop()

# ----------------------------------------------------------------- 2. Sheet
st.subheader("2. Sheet")

if not sheets:
    st.error("This workbook has no worksheets.")
    st.stop()

names = [s.name for s in sheets]
rows_by_name = {s.name: s.populated_rows for s in sheets}
current_sheet = state["sheet"] if state["sheet"] in names else names[0]

chosen_sheet = st.selectbox(
    "Sheet",
    options=names,
    index=names.index(current_sheet),
    key=f"pe::book::{state['path']}::sheet",
    # The row count is what stops a 99%-blank template sheet from looking like
    # a broken plot.
    format_func=lambda n: f"{n} — {rows_by_name[n]} row(s) of data",
)

if chosen_sheet != state["sheet"]:
    state["sheet"] = chosen_sheet
    reset_sheet_selections(state)
    remembered = config_store.load_sheet_state(chosen_sheet)
    if remembered:
        state["coercions"] = remembered.get("coercions", {})
        state["filters"] = remembered.get("filters", [])
        state["config"] = {**scatter.DEFAULT_CONFIG, **remembered.get("config", {})}
    config_store.save_last_location(state["path"], chosen_sheet)
    st.rerun()

try:
    frame = _cached_frame(state["path"], _mtime(state["path"]), state["sheet"], state["header_rows"])
except Exception as e:
    st.error(f"Could not read sheet '{state['sheet']}': {e}")
    st.stop()

if frame.empty:
    st.warning(
        f"Sheet '{state['sheet']}' has no data below its {state['header_rows']} header row(s)."
    )
    st.stop()

# A config remembered when the sheet had different columns must not be able to
# break the page; unknown columns come back unset.
state["config"] = config_store.prune_to_columns(state["config"], frame.columns)


def K(name: str) -> str:
    """An explicit, sheet-scoped widget key.

    Streamlit derives a keyless widget's identity from a hash of its label,
    options and index. Two sheets with identical columns therefore produce the
    *same* widget -- and ``VAHA_SplitTable`` and ``VB_SplitTable`` in a real
    process workbook have byte-identical column sets -- so one sheet's
    selection silently carries onto the other's data. Keying every control
    below by sheet name means switching sheets always builds new widgets,
    whatever the columns happen to be.
    """
    return f"pe::{state['path']}::{state['sheet']}::{name}"

# --------------------------------------------------------------- 3. Columns
st.subheader("3. Columns")

profiles = source.profile_columns(frame)
mixed = [p for p in profiles if p.kind == "mixed"]

st.caption(
    f"{len(frame)} rows × {len(frame.columns)} columns. "
    + (
        f"{len(mixed)} column(s) hold both numbers and text — Plotly will treat those as "
        "categories unless they are coerced."
        if mixed else "No column mixes numbers and text."
    )
)

with st.expander("Column table and numeric coercion", expanded=bool(mixed)):
    st.dataframe(
        [
            {
                "Column": p.name,
                "Type": p.kind,
                "Filled": p.filled,
                "Distinct": p.distinct,
                "Numbers": p.numeric,
                "Text": p.text,
                "Text examples": ", ".join(p.examples),
            }
            for p in profiles
        ],
        use_container_width=True,
        hide_index=True,
    )

    coercible = [p.name for p in profiles if p.kind in ("mixed", "text")]
    selected = st.multiselect(
        "Columns to read as numbers",
        options=coercible,
        default=[c for c in state["coercions"] if c in coercible],
        key=K("coerce_columns"),
        help="Only needed for a column whose numbers are stored as text.",
    )

    coercions = {}
    for name in selected:
        # "none" is not offered: a column listed above is one the user asked to
        # convert, and un-listing it is how you say no. A remembered value that
        # isn't one of these (a hand-edited settings file, say) falls back to
        # the first rather than raising.
        remembered = state["coercions"].get(name)
        index = STRATEGY_CHOICES.index(remembered) if remembered in STRATEGY_CHOICES else 0
        strategy = st.selectbox(
            f"'{name}' strategy",
            options=STRATEGY_CHOICES,
            index=index,
            key=K(f"strategy::{name}"),
            format_func=lambda s: source.COERCION_LABELS[s],
        )
        coercions[name] = strategy

        preview = source.coercion_preview(frame[name], strategy)
        if preview:
            result = source.coerce_column(frame[name], strategy)
            st.caption(
                "   ".join(f"`{before}` → `{after}`" for before, after in preview)
                + (f"  ·  **{result.lost} value(s) become blank**" if result.lost else "")
            )
        else:
            st.caption("Nothing in this column needs converting.")

    state["coercions"] = coercions

frame, losses = source.apply_coercions(frame, state["coercions"])
for name, lost in losses.items():
    st.warning(f"'{name}': {lost} value(s) could not be read as numbers and are now blank.")

# --------------------------------------------------------------- 4. Filters
st.subheader("4. Filters")

with st.expander("Exclude rows", expanded=bool(state["filters"])):
    st.caption(
        "A logbook sheet holds maintenance entries and unrelated experiments alongside "
        "the runs you want. Rows with no value in a filtered column are excluded."
    )
    remembered_filters = {f["column"]: f for f in state["filters"] if "column" in f}
    filter_columns = st.multiselect(
        "Filter on",
        options=[str(c) for c in frame.columns],
        default=[c for c in remembered_filters if c in frame.columns],
        max_selections=2,
        key=K("filter_columns"),
    )

    filters = []
    for name in filter_columns:
        previous = remembered_filters.get(name, {})
        series = frame[name]
        numeric = series.dropna() if series.dtype.kind in "if" else None
        # st.slider raises when its two bounds are equal, which a column of one
        # repeated value (or no values at all) would produce -- a real shape in
        # a process sheet where one parameter was held constant.
        if numeric is not None and len(numeric) and float(numeric.min()) < float(numeric.max()):
            low, high = float(numeric.min()), float(numeric.max())
            chosen_low, chosen_high = st.slider(
                f"'{name}' range",
                min_value=low, max_value=high,
                value=(
                    max(low, float(previous.get("minimum", low))),
                    min(high, float(previous.get("maximum", high))),
                ),
                key=K(f"range::{name}"),
            )
            filters.append({"column": name, "minimum": chosen_low, "maximum": chosen_high})
        elif numeric is not None:
            only = f"every row holds {numeric.iloc[0]:g}" if len(numeric) else "no values at all"
            st.caption(f"'{name}' has nothing to narrow — {only}.")
            # Recorded with no bounds, which `apply_filters` skips. Without it
            # the column would vanish from the multiselect on the next rerun,
            # so choosing it would look like the click didn't register.
            filters.append({"column": name})
        else:
            options = source.distinct_values(series)
            keep = st.multiselect(
                f"'{name}' — keep",
                options=options,
                default=[v for v in previous.get("keep", options) if v in options],
                key=K(f"keep::{name}"),
            )
            filters.append({"column": name, "keep": list(keep)})

    state["filters"] = filters

row_filters = [
    source.RowFilter(
        column=f["column"],
        keep=tuple(f["keep"]) if "keep" in f else None,
        minimum=f.get("minimum"),
        maximum=f.get("maximum"),
    )
    for f in state["filters"]
]
plotted = source.apply_filters(frame, row_filters)

if row_filters:
    st.caption(f"{len(plotted)} of {len(frame)} rows kept.")

if plotted.empty:
    st.warning("No rows survive the current filters.")
    st.stop()

# ------------------------------------------------------------------ 5. Plot
st.subheader("5. Plot")

config = state["config"]
columns = [str(c) for c in plotted.columns]
numeric = scatter.numeric_columns(plotted)

with st.expander("Axes", expanded=not (config.get("x") and config.get("y"))):
    c1, c2 = st.columns(2)
    with c1:
        config["x"] = _column_select("X", columns, config.get("x"), K("x"))
        config["log_x"] = st.checkbox(
            "Log X", value=bool(config.get("log_x")), key=K("log_x")
        )
        config["range_x_min"] = st.number_input(
            "X min", value=config.get("range_x_min"), placeholder="auto", format="%g",
            key=K("range_x_min")
        )
        config["range_x_max"] = st.number_input(
            "X max", value=config.get("range_x_max"), placeholder="auto", format="%g",
            key=K("range_x_max")
        )
    with c2:
        config["y"] = _column_select("Y", columns, config.get("y"), K("y"))
        config["log_y"] = st.checkbox(
            "Log Y", value=bool(config.get("log_y")), key=K("log_y")
        )
        config["range_y_min"] = st.number_input(
            "Y min", value=config.get("range_y_min"), placeholder="auto", format="%g",
            key=K("range_y_min")
        )
        config["range_y_max"] = st.number_input(
            "Y max", value=config.get("range_y_max"), placeholder="auto", format="%g",
            key=K("range_y_max")
        )
    st.caption("An axis range applies only when both ends are set.")

with st.expander("Encoding"):
    c1, c2 = st.columns(2)
    with c1:
        config["color"] = _column_select("Colour", columns, config.get("color"), K("color"))
        config["symbol"] = _column_select("Symbol", columns, config.get("symbol"), K("symbol"))
        config["size"] = _column_select(
            "Size", numeric, config.get("size"), K("size"),
            help_text="Numeric columns only — Plotly cannot size a marker by text.",
        )
    with c2:
        config["size_max"] = st.slider(
            "Largest marker", min_value=5, max_value=60, value=int(config.get("size_max") or 20),
            key=K("size_max")
        )
        config["opacity"] = st.slider(
            "Opacity", min_value=0.1, max_value=1.0, value=float(config.get("opacity") or 0.8),
            key=K("opacity")
        )
        config["hover_name"] = _column_select(
            "Hover title", columns, config.get("hover_name"), K("hover_name")
        )
    config["hover_data"] = st.multiselect(
        "Extra hover fields",
        options=columns,
        default=[c for c in (config.get("hover_data") or []) if c in columns],
        key=K("hover_data"),
    )

with st.expander("Structure"):
    c1, c2 = st.columns(2)
    with c1:
        config["facet_row"] = _column_select(
            "Facet rows", columns, config.get("facet_row"), K("facet_row")
        )
        config["facet_col"] = _column_select(
            "Facet columns", columns, config.get("facet_col"), K("facet_col")
        )
        config["facet_col_wrap"] = st.number_input(
            "Wrap facet columns after", min_value=0, max_value=12,
            value=int(config.get("facet_col_wrap") or 0), step=1,
            key=K("facet_col_wrap"),
            help="0 leaves them on one row.",
        )
        trendline_options = list(scatter.TRENDLINE_CHOICES)
        config["trendline"] = st.selectbox(
            "Trendline",
            options=trendline_options,
            index=trendline_options.index(config.get("trendline") or ""),
            key=K("trendline"),
            format_func=lambda s: NONE_LABEL if s == "" else s,
            disabled=not scatter.statsmodels_available(),
            help=None if scatter.statsmodels_available() else "Requires statsmodels.",
        )
    with c2:
        config["error_x"] = _column_select(
            "X error bars", numeric, config.get("error_x"), K("error_x")
        )
        config["error_y"] = _column_select(
            "Y error bars", numeric, config.get("error_y"), K("error_y")
        )
        marginals = list(scatter.MARGINAL_CHOICES)
        config["marginal_x"] = st.selectbox(
            "Marginal X", options=marginals,
            index=marginals.index(config.get("marginal_x") or ""),
            key=K("marginal_x"),
            format_func=lambda s: NONE_LABEL if s == "" else s,
        )
        config["marginal_y"] = st.selectbox(
            "Marginal Y", options=marginals,
            index=marginals.index(config.get("marginal_y") or ""),
            key=K("marginal_y"),
            format_func=lambda s: NONE_LABEL if s == "" else s,
        )

with st.expander("Style"):
    templates = list(scatter.TEMPLATE_CHOICES)
    config["template"] = st.selectbox(
        "Template", options=templates,
        index=templates.index(config.get("template")) if config.get("template") in templates else 1,
        key=K("template"),
    )
    config["title"] = st.text_input("Title", value=config.get("title") or "", key=K("title"))

for warning in scatter.cardinality_warnings(plotted, config):
    st.warning(warning)

figure = None
if not (config.get("x") and config.get("y")):
    st.info("Choose an X and a Y column under **Axes** to draw the plot.")
else:
    try:
        figure = scatter.build_scatter(plotted, config)
    except ValueError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Plotly could not draw this: {e}")

if figure is not None:
    render_plot(figure, key=K("chart"))

    st.subheader("6. Export")
    default_stem = f"{state['sheet']}_scatter"
    col_png, col_html, col_mode = st.columns([1, 1, 2])

    with col_mode:
        self_contained = st.checkbox(
            "Self-contained HTML", value=True, key=K("self_contained"),
            help=(
                "Embeds plotly.js (~3 MB larger) so the file opens with no internet. "
                "Uncheck for a small file that loads the library from a CDN."
            ),
        )
    with col_png:
        if st.button("Save PNG", use_container_width=True):
            target = prompt_save_path(
                default_dir=os.path.dirname(state["path"]),
                default_filename=f"{default_stem}.png",
                title="Save Plot as PNG",
                filetypes=(("PNG images", "*.png"), ("All files", "*.*")),
                default_extension=".png",
            )
            if target:
                try:
                    with open(target, "wb") as f:
                        f.write(export_figure_png(figure))
                    st.success(f"Saved {target}")
                except Exception as e:
                    st.error(f"PNG export failed: {e}")
    with col_html:
        if st.button("Save HTML", use_container_width=True):
            target = prompt_save_path(
                default_dir=os.path.dirname(state["path"]),
                default_filename=f"{default_stem}.html",
                title="Save Plot as HTML",
                filetypes=(("HTML files", "*.html"), ("All files", "*.*")),
                default_extension=".html",
            )
            if target:
                try:
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(export_figure_html(figure, self_contained=self_contained))
                    st.success(f"Saved {target}")
                except Exception as e:
                    st.error(f"HTML export failed: {e}")

# Remembered per sheet, and only when something actually changed — this runs on
# every widget interaction, and rewriting the file on each slider tick would be
# a write per frame of a drag.
snapshot = {
    "header_rows": state["header_rows"],
    "coercions": state["coercions"],
    "filters": state["filters"],
    "config": config,
}
if state["sheet"] and snapshot != state.get("_saved"):
    config_store.save_sheet_state(state["sheet"], snapshot)
    config_store.save_last_location(state["path"], state["sheet"])
    state["_saved"] = {
        "header_rows": snapshot["header_rows"],
        "coercions": dict(snapshot["coercions"]),
        "filters": [dict(f) for f in snapshot["filters"]],
        "config": dict(snapshot["config"]),
    }
